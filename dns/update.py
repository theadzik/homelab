import requests
import json

IP_URL = "https://ifconfig.me"

BASE_URL = "https://www.spaceship.com"
LOGIN_API = "/connect/token"
UPDATE_API = "/gateway/api/v1/advanceddnsbff/dnsrecords/bulkUpdate"

public_ip = requests.request("GET", IP_URL).text

with open("payload_template.json", "r") as payload_template:
    payload = json.load(payload_template)
    payload["recordsToUpdate"]["0819888a-318a-433d-84f6-c39f706190ea"]["address"] = public_ip

with open("secrets.json", "r") as secrets:
    config = json.load(secrets)
    params = {
        "client_id": "spaceship",
        "grant_type": "password",
        "username": config['username'],
        "password": config['password'],
    }

    cookies = {
        "z-account-deviceid": config['z-account-deviceid'],
    }

login_response = requests.request(method="POST", url=BASE_URL + LOGIN_API, data=params, cookies=cookies)
bearer_token = json.loads(login_response.text)["access_token"]

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {bearer_token}",
}

update = requests.request(
    method="POST",
    url=BASE_URL + UPDATE_API,
    headers=headers,
    json=payload,
    cookies=cookies,
)

print(update.status_code, update.text)
