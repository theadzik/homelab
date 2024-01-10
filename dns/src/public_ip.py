import logging

import requests


class PublicIP:
    def __init__(self, config: dict):
        self.config = config

    @staticmethod
    def get_public_ip() -> str:
        ip_url = "https://ifconfig.me"
        public_ip = requests.request("GET", ip_url)
        try:
            public_ip.raise_for_status()
            logging.info(f"Current Public IP - {public_ip.text}")
            return public_ip.text
        except Exception as e:
            logging.error(f"Failed getting Public IP. Status code {public_ip.status_code}, Response: {public_ip.text}")
            raise e

    def save_public_ip(self, public_ip: str) -> None:
        log_path = self.config["IP_HISTORY_PATH"]
        with open(log_path, "a") as ip_log:
            ip_log.write(public_ip + "\n")

    def get_previous_public_ip(self) -> str:
        log_path = self.config["IP_HISTORY_PATH"]
        try:
            with open(log_path, "r") as ip_log:
                return list(ip_log)[-1].strip()
        except FileNotFoundError:
            return ""
