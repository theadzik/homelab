import json
import logging

import requests

BASE_URL = "https://www.spaceship.com"
LOGIN_API = "/connect/token"
UPDATE_API = "/gateway/api/v1/advanceddnsbff/dnsrecords/bulkUpdate"


def get_payload(template_path: str, public_ip: str, record_id: str) -> dict:
    with open(template_path, "r") as payload_template:
        payload = json.load(payload_template)

    payload["recordsToUpdate"][record_id]["address"] = public_ip
    logging.debug(f"Generated payload={payload}")
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
    if login_response.ok:
        bearer_token = json.loads(login_response.text)["access_token"]
        logging.debug("Got bearer token")
        return bearer_token
    else:
        logging.error(f"Failed to get bearer token. Status code {login_response.status_code}, Response: {login_response.text}")


def update_dns_entry(bearer_token: str, device_token: str, payload: dict):
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

    try:
        update.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to update dns. Status code {update.status_code}, Response: {update.text}")
        raise e

    logging.debug(f"Updated DNS. Status code {update.status_code}, Response: {update.text}")
    return update.json()
