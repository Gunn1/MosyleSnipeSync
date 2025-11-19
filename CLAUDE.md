# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MosyleSnipeSync is a Python-based synchronization tool that integrates Apple device data between two mobile device management platforms:
- **Mosyle**: Apple-specific device management system
- **Snipe-IT**: Open-source asset management and IT inventory system

The tool pulls device information from Mosyle (Mac, iOS, tvOS), creates/updates assets in Snipe-IT, manages device assignments, and syncs asset tags between systems.

## Architecture

### Core Components

**Main Entry Point** (`main.py:1-135`)
- Orchestrates the sync workflow for each device type (mac, ios, tvos)
- Loads configuration from `settings.ini`
- For each device type: fetches devices from Mosyle → processes each device → updates Snipe-IT
- Uses `rich` library for progress bar visualization

**Mosyle Integration** (`mosyle.py`)
- `Mosyle` class handles authentication and API communication with Mosyle
- Login flow: uses `access_token`, `email`, and `password` to obtain JWT token via `/login` endpoint
- Key methods:
  - `list(os, page)`: Paginated device listing for a specific OS type
  - `setAssetTag(serialnumber, tag)`: Updates device asset tag in Mosyle
- Maintains authenticated session with Bearer token in headers

**Snipe-IT Integration** (`snipe.py`)
- `Snipe` class manages all Snipe-IT API interactions
- Constructor takes extensive config: API key, categories, fieldsets, rate limit, manufacturer ID
- Key responsibilities:
  - **Model Management**: Creates/searches Mac, iOS, tvOS models with hardcoded custom field IDs
  - **Asset Operations**: Creates, updates, lists hardware; manages assignments/checkouts
  - **Image Handling**: Fetches Apple device images from `api.appledb.dev` and encodes as base64 data URIs
  - **Rate Limiting**: Tracks requests and sleeps for 60s when limit (default 120/min) is exceeded
  - **Retry Logic**: Implements exponential backoff for 429/5xx errors up to 5 attempts
- Payload building maps Mosyle device fields to hardcoded Snipe-IT custom field IDs (e.g., `_snipeit_cpu_family_7`)

**Apple Info Utility** (`appleInfo.py`)
- Standalone script for retroactively updating images on Apple models in Snipe-IT
- Processes all models, filters by Apple manufacturer, downloads images via AppleDB if missing
- Useful for backfill operations

### Data Flow

1. Configuration parameters (including Mosyle credentials) loaded from `settings.ini`
2. For each device type in `settings.ini` → `mosyle.deviceTypes`:
   - Query Mosyle for devices (paginated if using "all" calltype)
   - For each Mosyle device:
     - Search Snipe-IT by serial number
     - If model doesn't exist, create it (with image from AppleDB if `apple_image_check` enabled)
     - Create or update asset with device data
     - Sync user assignment if device has console-managed user
     - Update Mosyle asset tag with Snipe-IT's generated asset tag

### Configuration

**settings.ini** has 3 sections:
- `[mosyle]`: Mosyle API credentials and device type filtering
- `[snipe-it]`: Snipe-IT URL, API key, category/fieldset IDs, rate limit, image checking
- `[api-mapping]`: Field mapping (partially defined, expandable)

Critical custom field IDs in `snipe.py:buildPayloadFromMosyle()` are hardcoded:
- `_snipeit_cpu_family_7`, `_snipeit_percent_disk_5`, `_snipeit_available_disk_5`, `_snipeit_os_info_6`, `_snipeit_osversion_12`, `_snipeit_mac_address_1`, `_snipeit_bluetooth_mac_address_11`

These must match your Snipe-IT custom field IDs or assets will be created with missing data.

## Development Commands

### Setup
```bash
# Install dependencies
pip3 install -r requirements.txt

# Copy and configure settings
cp settings_example.ini settings.ini
# Edit settings.ini with your Mosyle and Snipe-IT credentials and configuration
```

### Running

#### One-Time Sync
```bash
# Full sync of configured device types (runs once and exits)
python3 main.py

# With custom config and logging directory
python3 main.py --config /path/to/settings.ini --log-dir ./logs --log-level INFO

# Enable debug logging
python3 main.py --log-level DEBUG

# Backfill Apple model images
python3 appleInfo.py
```

#### Daemon Mode (Continuous Loop)
```bash
# Run continuously with 1-hour interval (3600 seconds)
python3 main.py --daemon --interval 3600

# Run with 30-minute interval
python3 main.py --daemon --interval 1800

# Exit with Ctrl+C
```

#### Command-Line Arguments
- `--daemon`: Run continuously in loop mode instead of one-time execution
- `--interval SECONDS`: Time between runs in daemon mode (default: 3600 = 1 hour)
- `--config FILE`: Path to settings.ini (default: settings.ini)
- `--log-dir DIR`: Directory for log files (default: logs)
- `--log-level LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO)

### Scheduled Deployment (systemd)

The recommended production approach uses Linux systemd with a timer for reliable scheduled execution.

#### Installation

```bash
# 1. Prepare settings and credentials
cp settings_example.ini ~/mosyle-config/settings.ini
# Edit ~/mosyle-config/settings.ini with your Mosyle and Snipe-IT credentials

# 2. Run installation script as root
sudo bash install_systemd.sh ~/mosyle-config/settings.ini
```

This script will:
- Create a `mosyle-snipe` system user
- Create `/opt/mosyle-snipe-sync` application directory
- Create `/etc/mosyle-snipe-sync` config directory
- Create `/var/log/mosyle-snipe-sync` log directory
- Set up Python virtual environment with dependencies
- Install systemd service and timer files
- Set proper file permissions

#### Managing the Service

```bash
# Enable timer to run at boot
sudo systemctl enable mosyle-snipe-sync.timer

# Start the timer
sudo systemctl start mosyle-snipe-sync.timer

# Check timer status
sudo systemctl status mosyle-snipe-sync.timer
systemctl list-timers mosyle-snipe-sync.timer

# View upcoming run times
sudo systemctl list-timers --all mosyle-snipe-sync.timer

# Stop the timer
sudo systemctl stop mosyle-snipe-sync.timer

# Run immediately (don't wait for next scheduled time)
sudo systemctl start mosyle-snipe-sync.service
```

#### Modifying the Schedule

The default schedule is **every 1 hour**, with the first run 10 minutes after boot.

To change the interval, edit the timer file:

```bash
sudo nano /etc/systemd/system/mosyle-snipe-sync.timer
```

Common OnUnitActiveSec values:
- `1h`: Every 1 hour
- `6h`: Every 6 hours
- `12h`: Every 12 hours
- `1d`: Every 24 hours

To run at a specific time (e.g., 2 AM daily):

```bash
# Replace "OnUnitActiveSec=1h" with:
OnCalendar=02:00
```

After editing, reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart mosyle-snipe-sync.timer
```

#### Viewing Logs

```bash
# View systemd journal (real-time)
sudo journalctl -u mosyle-snipe-sync.service -f

# View last 100 lines
sudo journalctl -u mosyle-snipe-sync.service -n 100

# View logs from last hour
sudo journalctl -u mosyle-snipe-sync.service --since "1 hour ago"

# View log files directly
tail -f /var/log/mosyle-snipe-sync/mosyle_snipe_sync.log

# View with grep filter
journalctl -u mosyle-snipe-sync.service | grep "ERROR"
```

### Testing Considerations
- Mosyle API is destructive (can remove ADMIN rights) — test carefully on non-prod first
- Rate limiting is enforced by Snipe-IT (default 120 req/min) — script auto-sleeps when limit is hit
- Serial number must exist in Mosyle for device to sync (devices without serial are skipped)
- User assignment requires matching email between Mosyle and Snipe-IT user accounts
- When testing with systemd, check both `journalctl` and `/var/log/mosyle-snipe-sync/` for full logs

## Common Development Tasks

### Adding Support for a New Device Type
1. Ensure Mosyle supports the device type (`mac`, `ios`, `tvos` are supported)
2. Add new category ID to `settings.ini`
3. Add corresponding `createXxxModel()` method in `snipe.py`
4. Update device type loop in `main.py` to call appropriate model creation

### Mapping Additional Mosyle Fields to Snipe-IT
1. Identify Snipe-IT custom field ID for the target field
2. Add mapping in `snipe.py:buildPayloadFromMosyle()` with hardcoded field ID
3. Update `settings.ini` `[api-mapping]` section for documentation

### Debugging API Issues
- Enable debug output: Check colorama colored print statements in code
- Mosyle auth fails: Verify admin credentials in `settings.ini` [mosyle] section and that admin has API access
- Snipe-IT rate limit hit: Script automatically waits 60s; check if genuine API usage is exceeding limit
- Model/asset creation fails: Verify category IDs and manufacturer ID exist in Snipe-IT

## Known Issues & Limitations

1. **Hardcoded Custom Field IDs**: The `_snipeit_*` field IDs in `snipe.py:buildPayloadFromMosyle()` must match your Snipe-IT instance exactly. No configuration-driven approach currently exists.

2. **BYOB Logic**: User-enrolled devices in Mosyle are assumed to be BYOB and skipped entirely. May not fit all organizations.

3. **Timestamp Calltype**: The "timestamp" mode in `settings.ini` for incremental syncs is noted as potentially non-functional.

4. **Print Verbosity**: Original codebase has extensive print statements for debugging. Production users may find output verbose.

5. **No Transaction Rollback**: If sync fails mid-process, partial updates remain. No atomic transaction handling.

## Security Considerations

- Store Mosyle and Snipe-IT credentials in `settings.ini`, never commit credentials to version control
- Ensure `settings.ini` has restrictive file permissions (e.g., `chmod 600 settings.ini`)
- Snipe-IT API key should be restricted to read/write asset and model operations
- Rate limiting is built-in but ensure your Snipe-IT instance is properly configured
- AppleDB image fetching is over HTTPS but integrates external image data

## Deployment & Operations

### Logging System

The refactored codebase includes comprehensive logging with file rotation:

- **Logs directory**: `logs/` by default (configurable with `--log-dir`)
- **Log file**: `mosyle_snipe_sync.log`
- **Rotation**: Files rotate at 10MB, keeping 10 backups
- **Format**: `[YYYY-MM-DD HH:MM:SS] LEVEL message`
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

When deployed with systemd:
- Logs go to both file (`/var/log/mosyle-snipe-sync/`) and systemd journal
- Use `journalctl` for real-time monitoring
- Log directory permissions are set to 755

### Failure Handling

- **Non-fatal errors**: Device processing errors are logged and skipped; sync continues with remaining devices
- **API connection failures**: Logged and retried according to Snipe-IT retry logic (429/5xx errors)
- **Missing config/credentials**: Script exits with fatal error and logs details
- **Daemon mode**: Errors in one run don't stop the daemon; next run occurs at scheduled interval

### Operational Monitoring

**Key metrics in logs:**
- Total devices processed per run
- Devices created vs. updated
- User assignment changes
- Asset tag synchronization events
- API errors and rate limit hits

**Health checks:**
```bash
# Is the timer enabled and running?
sudo systemctl is-enabled mosyle-snipe-sync.timer
sudo systemctl is-active mosyle-snipe-sync.timer

# When will the next run occur?
sudo systemctl list-timers mosyle-snipe-sync.timer

# Did the last run succeed?
sudo journalctl -u mosyle-snipe-sync.service -n 50 | grep "Synchronization run complete"
```

## Dependencies

- **colorama**: Terminal color output
- **requests**: HTTP library for API calls
- **rich**: Progress bars and console formatting
- **configparser**: Built-in, parse `settings.ini`
- **logging**: Built-in, structured logging with rotation
