import logging
import os
import platform
import signal
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
            url="https://httpstat.us/500",  # self.update_url,
            headers=self.get_headers()
        )

        result = self.handle_response(update)
        return result

    def handle_response(self, response: requests.Response) -> bool:
        # https://www.noip.com/integrate/response
        match response.text:
            case r"good.*":
                logging.info(f"Updated DNS. [{response.status_code}] {response.text}")
                return True
            case r"nochg.*":
                logging.warning(f"No changes. [{response.status_code}] {response.text}")
                return True
            case r"nohost|badauth|badagent|\!donator|abuse":
                logging.critical(f"Failed to update DNS: [{response.status_code}] {response.text}")
                # TODO: Send email
                logging.info(f"Send an email to {self.maintainer_email}")
                signal.pause()
            case "911":
                logging.warning(f"Failed to update DNS: [{response.status_code}] {response.text}")
            case _:
                logging.error(f"Did not understand response: [{response.status_code}] {response.text}")
        return False
