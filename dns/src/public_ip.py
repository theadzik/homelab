import logging

import requests


def get_public_ip() -> str:
    ip_url = "https://ifconfig.me"
    public_ip = requests.request("GET", ip_url)
    if public_ip.ok:
        logging.info(f"PublicIP - {public_ip.text}")
        return public_ip.text
    else:
        logging.error(f"Failed getting Public IP. Status code {public_ip.status_code}, Response: {public_ip.text}")
