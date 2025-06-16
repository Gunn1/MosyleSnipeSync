import requests
import json
import datetime
import configparser
from colorama import Fore, Style, init
from snipe import Snipe

# Initialize colorama for colored terminal output
init()

# Load config
config = configparser.ConfigParser()
config.read('settings.ini')

snipe_url = config['snipe-it']['url']
apiKey = config['snipe-it']['apiKey']
defaultStatus = config['snipe-it']['defaultStatus']
apple_manufacturer_id = int(config['snipe-it']['manufacturer_id'])
macos_category_id = config['snipe-it']['macos_category_id']
ios_category_id = config['snipe-it']['ios_category_id']
tvos_category_id = config['snipe-it']['tvos_category_id']
macos_fieldset_id = config['snipe-it']['macos_fieldset_id']
ios_fieldset_id = config['snipe-it']['ios_fieldset_id']
tvos_fieldset_id = config['snipe-it']['tvos_fieldset_id']
snipe_rate_limit = int(config['snipe-it']['rate_limit'])
apple_image_check = config['snipe-it'].getboolean('apple_image_check')

# Initialize Snipe API
snipe = Snipe(apiKey, snipe_url, apple_manufacturer_id, macos_category_id, ios_category_id, tvos_category_id,
              snipe_rate_limit, macos_fieldset_id, ios_fieldset_id, tvos_fieldset_id, apple_image_check)

# Fetch all models
try:
    response = snipe.listAllModels()
    models = response.json()
except Exception as e:
    print(Fore.RED + f"Failed to get models: {e}" + Style.RESET_ALL)
    exit(1)

if 'rows' not in models:
    print(Fore.RED + "No models found in response." + Style.RESET_ALL)
    exit(1)

# Process models
for model in models['rows']:
    model_id = model.get('id')
    model_name = model.get("model_number") or model.get("name", "Unknown")
    print(f"Processing model: {model_id} {model_name}")

    manufacturer = model.get('manufacturer')
    if not manufacturer or 'id' not in manufacturer:
        print(Fore.YELLOW + f"Model {model_id} has no manufacturer info. Skipping." + Style.RESET_ALL)
        continue

    manufacturer_id = int(manufacturer['id'])
    print(f"Is the model's manufacturer Apple? checking manufacturer id {manufacturer_id} against {apple_manufacturer_id}")

    if manufacturer_id != apple_manufacturer_id:
        print(Fore.YELLOW + "Model is not Apple. Skipping." + Style.RESET_ALL)
        continue

    print(Fore.GREEN + "Yes! Checking for photo..." + Style.RESET_ALL)

    if not model.get('image'):
        print("No photo found. Attempting download...")

        try:
            image_response = snipe.getImageForModel(model_name)
            if image_response:
                print(Fore.CYAN + "Photo downloaded. Updating model..." + Style.RESET_ALL)

                payload = {"image": image_response}
                snipe.updateModel(str(model_id), payload)
            else:
                print(Fore.YELLOW + f"No photo found for model {model_name}. Skipping." + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error downloading image for model {model_name}: {e}" + Style.RESET_ALL)

    else:
        print("Picture already set. Skipping.")
