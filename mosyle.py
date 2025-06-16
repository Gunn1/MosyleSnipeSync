import requests

class Mosyle:
    def __init__(self, access_token, email, password, url="https://managerapi.mosyle.com/v2"):
        self.url = url
        self.access_token = access_token
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.jwt_token = self.login()

        if self.jwt_token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json"
            })
        else:
            raise Exception("Login failed. Could not obtain JWT token.")

    def login(self):
        payload = {
            "accessToken": self.access_token,
            "email": self.email,
            "password": self.password
        }
        response = self.session.post(f"{self.url}/login", json=payload)

        if response.status_code == 200:
            auth_header = response.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                return auth_header.replace("Bearer ", "")
            else:
                print("Authorization header missing or malformed.")
        else:
            print(f"Login failed. Status Code: {response.status_code}")
            print(f"Error: {response.text}")
        return None

    def _post(self, endpoint, data):
        data["accessToken"] = self.access_token
        response = self.session.post(f"{self.url}/{endpoint}", json=data)
        try:
            return response.json()
        except Exception:
            return {"error": "Invalid JSON response", "text": response.text}

    def list(self, os, specific_columns=None, page=1):
        print("Listing devices for OS:", os, "Page:", page)
        data = {
			"accessToken": self.access_token,
			"operation": "list",
			"options": {
				"os": os,
				"page": page
			}
		}
        if specific_columns:
            data["specific_columns"] = specific_columns
        return self._post("listdevices", data)
    def setAssetTag(self, serialnumber, tag):
        return self._post("devices", {
			"operation": "update_device",
			"serialnumber": serialnumber,
			"asset_tag": tag
		})
