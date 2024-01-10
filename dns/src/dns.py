import json
import logging

import requests


class HandlerDNS:
    def __init__(self, config: dict):
        self.base_url = "https://www.spaceship.com"
        self.config = config
        self.cookies = self.get_cookies()
        self.headers = self.get_headers()

    def get_payload(self, public_ip: str) -> dict:
        with open(self.config["DNS_TEMPLATE_PATH"], "r") as payload_template:
            payload = json.load(payload_template)

        # Only 1 key is expected in recordsToUpdate
        record_key = list(payload["recordsToUpdate"].keys())[0]

        payload["recordsToUpdate"][record_key]["address"] = public_ip
        logging.debug(f"Generated payload={payload}")
        return payload

    def get_cookies(self) -> dict:
        cookies = {
            "z-account-deviceid": self.config['DNS_DEVICE_TOKEN'],
        }
        return cookies

    def get_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.get_dns_token()}",
        }
        return headers

    def get_dns_token(self) -> str:
        login_api = "/connect/token"

        params = {
            "client_id": "spaceship",
            "grant_type": "password",
            "username": self.config['DNS_USERNAME'],
            "password": self.config['DNS_PASSWORD'],
        }

        logging.debug(f"Params: {params}")
        login_response = requests.request(
            method="POST",
            url=self.base_url + login_api,
            data=params,
            cookies=self.cookies
        )

        try:
            logging.debug(login_response)
            login_response.raise_for_status()
            bearer_token = json.loads(login_response.text)["access_token"]
            logging.debug("Got bearer token")
            return bearer_token
        except Exception as e:
            logging.error(
                f"Failed to get bearer token. "
                f"Status code {login_response.status_code}, Response: {login_response.text}"
            )
            raise e

    def update_dns_entry(self, payload: dict):
        update_api = "/gateway/api/v1/advanceddnsbff/dnsrecords/bulkUpdate"
        update = requests.request(
            method="POST",
            url=self.base_url + update_api,
            headers=self.headers,
            json=payload,
            cookies=self.cookies,
        )

        try:
            update.raise_for_status()
        except Exception as e:
            logging.error(f"Failed to update dns. Status code {update.status_code}, Response: {update.text}")
            raise e

        logging.debug(f"Updated DNS. Status code {update.status_code}, Response: {update.text}")
        return update.json()
