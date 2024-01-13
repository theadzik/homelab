import logging
import os
import platform
from base64 import b64encode

import requests


class HandlerDNS:
    def __init__(self, public_ip: str):
        self.username = os.environ["USERNAME"]
        self.password = os.environ["PASSWORD"]
        self.hostname = os.environ["HOSTNAME"]
        self.maintainer_email = os.environ["MAINTAINER_EMAIL"]
        self.public_ip = public_ip
        self.update_url = (
            "https://dynupdate.no-ip.com/nic/update"
            f"?hostname={self.hostname}"
            f"&myip={self.public_ip}"
        )

    def get_headers(self) -> dict:
        basic_auth = b64encode(f"{self.username}:{self.password}".encode()).decode()
        headers = {
            "Authorization": f"Basic {basic_auth}",
            "User-Agent": f"Homelab DNS-Updater/{platform.system()}{platform.release()}-3.0.0 {self.maintainer_email}"
        }
        return headers

    def update_dns_entry(self):
        update = requests.request(
            method="GET",
            url=self.update_url,
            headers=self.get_headers()
        )

        result = self.handle_response(update)
        return result

    def handle_response(self, response: requests.Response):
        match response.text:
            case r"good.*":
                logging.info(f"Updated DNS. {response.status_code} {response.text}")
                return 0
            case r"nochg.*":
                logging.warning(f"No changes. {response.status_code} {response.text}")
            case _:
                logging.error(f"Failed to update dns. Status code {response.status_code}, Response: {response.text}")
            # TODO: Add all errors and correct handling