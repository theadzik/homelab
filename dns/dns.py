import json
import requests

BASE_URL = "https://www.spaceship.com"
LOGIN_API = "/connect/token"
UPDATE_API = "/gateway/api/v1/advanceddnsbff/dnsrecords/bulkUpdate"


def get_payload(template_path: str, public_ip: str, record_id: str) -> dict:
    with open(template_path, "r") as payload_template:
        payload = json.load(payload_template)

    payload["recordsToUpdate"][record_id]["address"] = public_ip

    return payload


def get_dns_token(username: str, password: str, device_token: str) -> str:
    params = {
        "client_id": "spaceship",
        "grant_type": "password",
        "username": username,
        "password": password,
    }

    cookies = {
        "z-account-deviceid": device_token,
    }

    login_response = requests.request(method="POST", url=BASE_URL + LOGIN_API, data=params, cookies=cookies)
    bearer_token = json.loads(login_response.text)["access_token"]
    return bearer_token


def update_dns_entry(bearer_token: str, device_token: str, payload: dict) -> int:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
    }

    cookies = {
        "z-account-deviceid": device_token,
    }

    update = requests.request(
        method="POST",
        url=BASE_URL + UPDATE_API,
        headers=headers,
        json=payload,
        cookies=cookies,
    )

    return update.status_code
