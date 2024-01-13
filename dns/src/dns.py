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

    def update_dns_entry(self) -> bool:
        update = requests.request(
            method="GET",
            url=self.update_url,
            headers=self.get_headers()
        )

        try:
            update.raise_for_status()
        except requests.HTTPError as e:
            logging.error(f"Failed to update dns. Status code {update.status_code}, Response: {update.text}")
            raise e

        logging.info(f"Updated DNS. Status code {update.status_code}, Response: {update.text}")
        return update.ok
