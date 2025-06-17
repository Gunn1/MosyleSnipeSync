# Import all the things
import json
import datetime
import configparser
import colorama
from sys import exit

from mosyle import Mosyle
from snipe import Snipe
from colorama import Fore
from colorama import Style
import os
from dotenv import load_dotenv
from rich.progress import Progress
from rich.console import Console
from rich.style import Style

console = Console()

# Load the .env file
load_dotenv()

# Access the environment variables
mosyle_url = os.getenv("url")
mosyle_token = os.getenv("token")
mosyle_user = os.getenv("user")
mosyle_password = os.getenv("password")

# Converts datetime to timestamp for Mosyle
ts = datetime.datetime.now().timestamp() - 200

# Set some Variables from the settings.conf:
config = configparser.ConfigParser()
config.read('settings.ini')

snipe_url = config['snipe-it']['url']
apiKey = config['snipe-it']['apiKey']
defaultStatus = config['snipe-it']['defaultStatus']
apple_manufacturer_id = config['snipe-it']['manufacturer_id']
macos_category_id = config['snipe-it']['macos_category_id']
ios_category_id = config['snipe-it']['ios_category_id']
tvos_category_id = config['snipe-it']['tvos_category_id']
macos_fieldset_id = config['snipe-it']['macos_fieldset_id']
ios_fieldset_id = config['snipe-it']['ios_fieldset_id']
tvos_fieldset_id = config['snipe-it']['tvos_fieldset_id']
deviceTypes = config['mosyle']['deviceTypes'].split(',')

snipe_rate_limit = int(config['snipe-it']['rate_limit'])
apple_image_check = config['snipe-it'].getboolean('apple_image_check')

print(mosyle_token)
mosyle = Mosyle(mosyle_token, mosyle_user, mosyle_password, mosyle_url)
calltype = config['mosyle']['calltype']
snipe = Snipe(apiKey, snipe_url, apple_manufacturer_id, macos_category_id, ios_category_id, tvos_category_id, snipe_rate_limit, macos_fieldset_id, ios_fieldset_id, tvos_fieldset_id, apple_image_check)

total_devices_processed = 0

for deviceType in deviceTypes:
    if calltype == "timestamp":
        mosyle_response = mosyle.listTimestamp(ts, ts, deviceType)
    else:
        all_devices = []
        page = 1
        while True:
            response = mosyle.list(deviceType, page=page)
            devices = response.get('response', {}).get('devices', [])
            if not devices:
                break
            all_devices.extend(devices)
            page += 1
        mosyle_response = {"status": "OK", "response": {"devices": all_devices}}

    if mosyle_response.get('status') != "OK":
        print('There was an issue with the Mosyle API. Stopping.', mosyle_response.get('message'))
        exit()

    devices = mosyle_response['response'].get('devices', [])
    device_count = len(devices)

    with Progress() as progress:
        task = progress.add_task(f"[green]Processing {deviceType} devices...", total=device_count)

        for sn in devices:
            if sn['serial_number'] is None:
                progress.console.print("[yellow]Skipping device with no serial number.")
                progress.advance(task)
                continue

            asset = snipe.listHardware(sn['serial_number']).json()
            model = snipe.searchModel(sn['device_model']).json()
            if model['total'] == 0:
                if sn['os'] == "mac":
                    model = snipe.createModel(sn['device_model']).json()['payload']['id']
                elif sn['os'] == "ios":
                    model = snipe.createMobileModel(sn['device_model']).json()['payload']['id']
                elif sn['os'] == "tvos":
                    model = snipe.createAppleTvModel(sn['device_model']).json()['payload']['id']
            else:
                model = model['rows'][0]['id']
            mosyle_user = sn.get('useremail') if sn.get('CurrentConsoleManagedUser') and 'useremail' in sn else None
            devicePayload = snipe.buildPayloadFromMosyle(sn)

            if asset.get('total', 0) == 0:
                asset = snipe.createAsset(model, devicePayload)
                if mosyle_user:
                    snipe.assignAsset(mosyle_user, asset['payload']['id'])
                    progress.advance(task)
                    total_devices_processed += 1
                    continue

            if asset.get('total') == 1 and asset.get('rows'):
                snipe.updateAsset(asset['rows'][0]['id'], devicePayload, model)

            if mosyle_user:
                assigned = asset['rows'][0]['assigned_to']
                if assigned is None and sn.get('useremail'):
                    snipe.assignAsset(sn['useremail'], asset['rows'][0]['id'])
                elif sn.get('useremail') is None:
                    snipe.unasigneAsset(asset['rows'][0]['id'])
                elif assigned and assigned['username'] != sn['useremail']:
                    snipe.unasigneAsset(asset['rows'][0]['id'])
                    snipe.assignAsset(sn['useremail'], asset['rows'][0]['id'])

            asset_tag = asset['rows'][0].get('asset_tag') if asset.get('rows') else None
            if not sn.get('asset_tag') or sn['asset_tag'] != asset_tag:
                if asset_tag:
                    mosyle.setAssetTag(sn['serial_number'], asset_tag)

            total_devices_processed += 1
            progress.advance(task)

    console.print(f"[bold cyan]\n🎉 Finished {deviceType}: {total_devices_processed} total devices processed\n")

console.print(f"[bold green]✅ Script completed. Total devices processed: {total_devices_processed}")
