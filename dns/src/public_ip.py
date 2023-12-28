import logging

import requests


class PublicIP:
    def __init__(self, config: dict):
        self.config = config

    @staticmethod
    def get_public_ip() -> str:
        ip_url = "https://ifconfig.me"
        public_ip = requests.request("GET", ip_url)
        if public_ip.ok:
            logging.info(f"Current Public IP - {public_ip.text}")
            return public_ip.text
        else:
            logging.error(f"Failed getting Public IP. Status code {public_ip.status_code}, Response: {public_ip.text}")

    def save_public_ip(self, public_ip: str) -> None:
        log_path = self.config["ip_history_path"]
        with open(log_path, "a") as ip_log:
            ip_log.write(public_ip + "\n")

    def get_previous_public_ip(self) -> str:
        log_path = self.config["ip_history_path"]
        try:
            with open(log_path, "r") as ip_log:
                return list(ip_log)[-2]  # There is a new line at the end of the file so the last IP is in 2nd to last
        except FileNotFoundError:
            return ""
