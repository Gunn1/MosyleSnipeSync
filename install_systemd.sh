#!/bin/bash
# Installation script for MosyleSnipeSync systemd deployment
# Run as root: sudo bash install_systemd.sh [/path/to/config]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default paths
APP_DIR="/opt/mosyle-snipe-sync"
CONFIG_DIR="/etc/mosyle-snipe-sync"
LOG_DIR="/var/log/mosyle-snipe-sync"
USER="mosyle-snipe"
GROUP="mosyle-snipe"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root (use sudo)${NC}"
   exit 1
fi

echo -e "${GREEN}=== MosyleSnipeSync systemd Installation ===${NC}"

# Step 1: Check if settings.ini is provided
if [ $# -lt 1 ]; then
    echo -e "${YELLOW}Usage: sudo bash install_systemd.sh /path/to/settings.ini${NC}"
    echo "Example: sudo bash install_systemd.sh ~/mosyle-config/settings.ini"
    exit 1
fi

SETTINGS_FILE="$1"

if [ ! -f "$SETTINGS_FILE" ]; then
    echo -e "${RED}Error: settings.ini not found at $SETTINGS_FILE${NC}"
    exit 1
fi

# Step 2: Create system user and group
echo -e "${GREEN}Creating system user and group...${NC}"
if id "$USER" &>/dev/null; then
    echo "User $USER already exists"
else
    useradd --system --shell /bin/false --home-dir "$APP_DIR" "$USER" || echo "User $USER already exists"
fi

# Step 3: Create necessary directories
echo -e "${GREEN}Creating directories...${NC}"
mkdir -p "$APP_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"

# Step 4: Copy application files
echo -e "${GREEN}Copying application files...${NC}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cp "$SCRIPT_DIR"/*.py "$APP_DIR/" || true
cp "$SCRIPT_DIR"/requirements.txt "$APP_DIR/" 2>/dev/null || true

# Step 5: Copy and configure settings.ini
echo -e "${GREEN}Copying configuration file...${NC}"
cp "$SETTINGS_FILE" "$CONFIG_DIR/settings.ini"
chmod 600 "$CONFIG_DIR/settings.ini"

# Step 6: Copy .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${GREEN}Copying .env file...${NC}"
    cp "$SCRIPT_DIR/.env" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
else
    echo -e "${YELLOW}Warning: .env file not found. You'll need to create it manually.${NC}"
    echo "Create $APP_DIR/.env with your Mosyle credentials:"
    cat > "$APP_DIR/.env.example" << EOF
url=https://businessapi.mosyle.com/v1
token=your_token_here
user=admin_email@example.com
password=admin_password
EOF
    chmod 600 "$APP_DIR/.env.example"
    echo "Example .env file created at $APP_DIR/.env.example"
fi

# Step 7: Set permissions
echo -e "${GREEN}Setting permissions...${NC}"
chown -R "$USER:$GROUP" "$APP_DIR"
chown -R "$USER:$GROUP" "$CONFIG_DIR"
chown -R "$USER:$GROUP" "$LOG_DIR"
chmod 755 "$APP_DIR"
chmod 755 "$CONFIG_DIR"
chmod 755 "$LOG_DIR"

# Step 8: Create Python virtual environment
echo -e "${GREEN}Creating Python virtual environment...${NC}"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip setuptools wheel > /dev/null 2>&1

if [ -f "$APP_DIR/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
else
    echo -e "${YELLOW}requirements.txt not found, installing manually${NC}"
    "$APP_DIR/venv/bin/pip" install colorama requests rich python-dotenv
fi

# Step 9: Install systemd service and timer
echo -e "${GREEN}Installing systemd service and timer...${NC}"
cp "$SCRIPT_DIR/systemd/mosyle-snipe-sync.service" /etc/systemd/system/
cp "$SCRIPT_DIR/systemd/mosyle-snipe-sync.timer" /etc/systemd/system/

# Reload systemd daemon
systemctl daemon-reload

# Step 10: Final instructions
echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Verify configuration:"
echo "   cat $CONFIG_DIR/settings.ini"
echo ""
echo "2. If you haven't done so, create the .env file with Mosyle credentials:"
echo "   sudo cp $APP_DIR/.env.example $APP_DIR/.env"
echo "   sudo nano $APP_DIR/.env"
echo "   sudo chown $USER:$GROUP $APP_DIR/.env"
echo "   sudo chmod 600 $APP_DIR/.env"
echo ""
echo "3. Enable and start the timer:"
echo "   sudo systemctl enable mosyle-snipe-sync.timer"
echo "   sudo systemctl start mosyle-snipe-sync.timer"
echo ""
echo "4. Monitor the service:"
echo "   sudo systemctl status mosyle-snipe-sync.timer"
echo "   sudo systemctl list-timers mosyle-snipe-sync.timer"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u mosyle-snipe-sync.service -f"
echo "   or"
echo "   tail -f $LOG_DIR/mosyle_snipe_sync.log"
echo ""
echo "6. To change the run interval, edit the timer:"
echo "   sudo nano /etc/systemd/system/mosyle-snipe-sync.timer"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl restart mosyle-snipe-sync.timer"
echo ""
