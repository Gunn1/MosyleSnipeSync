import mimetypes
from unittest import result
import requests
import time
import base64
from colorama import Fore
from colorama import Style


class Snipe:
    def __init__(self, snipetoken, url,manufacturer_id,macos_category_id,ios_category_id,tvos_category_id,rate_limit,macos_fieldset_id,ios_fieldset_id,tvos_fieldset_id,apple_image_check):
        self.url = url
        self._snipetoken = snipetoken
        self.manufacturer_id = manufacturer_id
        self.macos_category_id = macos_category_id
        self.ios_category_id = ios_category_id
        self.tvos_category_id = tvos_category_id
        self.rate_limit = rate_limit
        self.request_count = 0
        self.macos_fieldset_id = macos_fieldset_id
        self.ios_fieldset_id = ios_fieldset_id
        self.tvos_fieldset_id = tvos_fieldset_id
        self.apple_image_check = apple_image_check

    @property
    def headers(self):
        return {
            "authorization": "Bearer " + self._snipetoken,
            "accept": "application/json",
            "content-type": "application/json",
        }    

    #@property
    def listHardware(self, serial):
        print('Requesting Snipe Harware list at url '+ self.url + "/hardware/byserial/")
        return self.snipeItRequest("GET", "/hardware/byserial/" + serial)

    def listAllModels(self):
        print('requesting all apple models')
        return self.snipeItRequest("GET","/models", params = {"limit": "200", "offset": "0", "sort": "created_at", "order": "asc"})

    def searchModel(self, model):
        print('Requesting Snipe Model list')
        result = self.snipeItRequest("GET", "/models", params={
            "limit": "50", "offset": "0", "search": model, "sort": "created_at", "order": "asc"
        })
        jsonResult = result.json()

        if jsonResult['total'] == 0:
            print("Model was not found.")
        else:
            print("Model was found.")
            model_data = jsonResult['rows'][0]

            if model_data['image'] is None:
                print("The model does not have a picture. Let's set one.")
                image_data_url = self.getImageForModel(model)

                if not image_data_url:
                    print("Failed to get image.")
                else:
                    payload = {
                        "image": image_data_url
                    }
                    self.updateModel(str(model_data['id']), payload)
            else:
                print("Image already set.")

        return result

    def createModel(self, model):

        imageResponse = self.getImageForModel(model);
        if(imageResponse == False):
            imageResponse = None

        payload = {
			"name": model,
            "category_id": self.macos_category_id,
            "manufacturer_id": self.manufacturer_id,
            "model_number": model,
            "fieldset_id": self.macos_fieldset_id,
            "image":imageResponse
        }

        print('Creating Snipe Model with payload:', payload)
        results = self.snipeItRequest("POST", "/models", json = payload)
        #print('the server returned ', results);
        return results

    def createAsset(self, model, payload):
        print('Creating Snipe Hardware')
        print(payload);
        payload['status_id'] = 2
        payload['model_id'] = model
        payload['asset_tag'] = payload['serial']
        
        #print(asset)
        return self.snipeItRequest("POST", "/hardware", json = payload).json()

    def assignAsset(self, user, asset_id):
        print('Assigning asset '+str(asset_id)+' to user '+user)
        
        payload = {
            "search": user,
            "limit": 2
        }
        response = self.snipeItRequest("GET", "/users", params = payload).json()

        if response['total'] == 0:
            return

        payload = {
            "assigned_user": response['rows'][0]['id'],
            "checkout_to_type": "user"
        }
        return self.snipeItRequest("POST", "/hardware/" + str(asset_id) + "/checkout", json = payload)

    def unasigneAsset(self, asset_id):
        print('Unassigning asset '+str(asset_id))
        return self.snipeItRequest("POST", "/hardware/" + str(asset_id) + "/checkin")

    def updateAsset(self, asset_id, payload, model_id=None):
        print('Updating asset ' + str(asset_id))
        payload = dict(payload)  # Make a copy to avoid mutating the original
        payload.pop('serial', None)

        if model_id:
            payload['model_id'] = model_id  # Include model assignment

        return self.snipeItRequest("PATCH", "/hardware/" + str(asset_id), json=payload)


    def createMobileModel(self, model):
        print('creating new mobile Model')
        imageResponse = self.getImageForModel(model);
        if(imageResponse == False):
            imageResponse = None
        payload = {
			"name": model,
            "category_id": self.ios_category_id,
            "manufacturer_id": self.manufacturer_id,
            "model_number": model,
            "fieldset_id": self.ios_fieldset_id,
            "image": imageResponse
        }
        return self.snipeItRequest("POST", "/models", json = payload)
    def createAppleTvModel(self, model):
        print('creating new Apple Tv Model')
        imageResponse = self.getImageForModel(model);
        if(imageResponse == False):
            imageResponse = None
        payload = {
			"name": model,
            "category_id": self.tvos_category_id,
            "manufacturer_id": self.manufacturer_id,
            "model_number": model,
            "fieldset_id": self.tvos_fieldset_id,
            "image": imageResponse
        }
        return self.snipeItRequest("POST", "/models", json = payload)

    def updateModel(self, model_id, payload):
        print("updating model "+model_id+" with payload", payload)
        return self.snipeItRequest("PATCH", "/models/"+model_id, json = payload)

    def buildPayloadFromMosyle(self, payload):
        finalPayload = {
            #"asset_tag": asset,
            "name": payload['device_name'],
            "serial": payload['serial_number'],
            "_snipeit_bluetooth_mac_address_11": payload['bluetooth_mac_address']
        }
        
        #lets get the proper os name
        if(payload['os'] == "mac"):
            os = "MacOS"
            #cpu stuff is only supplied by MacOS
            finalPayload["_snipeit_cpu_family_7"]: payload['cpu_model']

            finalPayload["_snipeit_percent_disk_5"]: payload['percent_disk'] + " GB"
            finalPayload["_snipeit_available_disk_5"]: payload['available_disk'] + " GB"
        elif(payload['os'] == "ios"):
            os = "iOS"
            finalPayload["_snipeit_percent_disk_5"]: payload['percent_disk'] + " GB"
            finalPayload["_snipeit_available_disk_5"]: payload['available_disk'] + " GB"
        elif(payload['os'] == "tvos"):
            os = "tvos"
        else:
            os = "Not Known"
        
                
        finalPayload['_snipeit_os_info_6'] = os
        
        #set os version
        finalPayload['_snipeit_osversion_12'] = payload['osversion']
        
        #macaddress stuff
        wifiMac = payload['wifi_mac_address']
        eithernetMac = payload['ethernet_mac_address']
        
        #default to eithernet mac, if not, fall back to wifi mac. If neither, leave blank
        if(wifiMac != None and eithernetMac == None):
            finalPayload['_snipeit_mac_address_1'] = wifiMac
        elif(eithernetMac != None):
            finalPayload['_snipeit_mac_address_1'] = eithernetMac
        
        return finalPayload

    def snipeItRequest(self, type, url, params=None, json=None):
        max_retries = 5
        retry_delay = 60  # seconds

        for attempt in range(max_retries):
            if self.request_count >= self.rate_limit:
                print(Fore.YELLOW + "Max requests per minute reached. Sleeping for 60 seconds..." + Style.RESET_ALL)
                time.sleep(60)
                self.request_count = 0

            try:
                self.request_count += 1
                print(f'Sending {type} request to Snipe-IT: {url}')

                if type == "GET":
                    response = requests.get(self.url + url, headers=self.headers, params=params)
                elif type == "POST":
                    response = requests.post(self.url + url, headers=self.headers, json=json)
                elif type == "PATCH":
                    response = requests.patch(self.url + url, headers=self.headers, json=json)
                elif type == "DELETE":
                    response = requests.delete(self.url + url, headers=self.headers)
                else:
                    print(Fore.RED + 'Unknown request type' + Style.RESET_ALL)
                    return None

                if response.status_code == 429:
                    print(Fore.YELLOW + f"Rate limited by server (429). Waiting {retry_delay} seconds before retrying..." + Style.RESET_ALL)
                    time.sleep(retry_delay)
                    continue

                if response.status_code >= 500:
                    print(Fore.RED + f"Server error {response.status_code}. Retrying in {retry_delay} seconds..." + Style.RESET_ALL)
                    time.sleep(retry_delay)
                    self.request_count = 0
                    continue

                return response

            except requests.RequestException as e:
                print(Fore.RED + f"Request failed: {e}. Retrying in {retry_delay} seconds..." + Style.RESET_ALL)
                time.sleep(retry_delay)

        print(Fore.RED + f"Failed to complete request after {max_retries} attempts: {url}" + Style.RESET_ALL)
        return None


    def getImageForModel(self, model_number):
        if not self.apple_image_check:
            print("Image checking is disabled.")
            return False

        print(f"Trying to look up model info from AppleDB: {model_number}")
        try:
            response = requests.get("https://api.appledb.dev/device/main.json")
            response.raise_for_status()
            devices = response.json()

            for device in devices:
                identifiers = device.get("identifier", [])
                device_maps = device.get("deviceMap", [])

                if model_number in device_maps or model_number in identifiers:
                    device_key = device.get("key", model_number)
                    colors = device.get("colors", [])
                    color = colors[0]["key"] if colors and isinstance(colors[0], dict) and "key" in colors[0] else "Silver"

                    image_url = f"https://img.appledb.dev/device@256/{device_key}/{color}.png"
                    print(f"Found match. Trying image URL: {image_url}")

                    img_response = requests.get(image_url)
                    img_response.raise_for_status()

                    base64encoded = base64.b64encode(img_response.content).decode("utf8")
                    full_image_string = "data:image/png;name=image.png;base64," + base64encoded
                    return full_image_string

            print(f"No matching identifier or deviceMap found for {model_number}")

        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Error getting image from AppleDB: {e}" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Unexpected error during AppleDB lookup: {e}" + Style.RESET_ALL)

        return False



    def setImageForModel(self, model_id, image_bytes):
        """
        Uploads an image to a model in Snipe-IT.

        :param model_id: ID of the model in Snipe-IT
        :param image_bytes: Raw image bytes (from requests.get().content)
        """
        url = f"{self.url}/models/{model_id}"
        headers = {
            "Authorization": f"Bearer {self._snipetoken}"
        }
        files = {
            "image": ("image.png", image_bytes, "image/png")
        }

        try:
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            print(Fore.GREEN + f"Successfully uploaded image for model ID {model_id}" + Style.RESET_ALL)
            return response
        except requests.RequestException as e:
            print(Fore.RED + f"Failed to upload image to model {model_id}: {e}" + Style.RESET_ALL)
            return None




        

#if __name__ == "__main__":
    #token_snipe = Snipe("Bearer = ".self.token)
    #test2 = token_snipe.list
    #print(test2.text)