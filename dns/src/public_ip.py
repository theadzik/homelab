import logging
from os import environ
import requests


def get_public_ip() -> str:
    remote_ip_detection_hosts = [
        "https://ifconfig.me",
        "https://ipinfo.io/ip",
        "https://ipecho.net/plain",
        "http://ip1.dynupdate.no-ip.com",
    ]
    for ip_url in remote_ip_detection_hosts:
        logging.debug(f"Requesting IP from {ip_url}")
        public_ip = requests.request("GET", ip_url)
        try:
            public_ip.raise_for_status()
            logging.info(f"Current Public IP: {public_ip.text}")
            return public_ip.text
        except requests.HTTPError:
            logging.error(
                f"Failed do get IP from {ip_url}.\n"
                f"Status code: {public_ip.status_code}\n"
                f"Response: {public_ip.text}"
            )


def save_public_ip(public_ip: str) -> None:
    log_path = environ["IP_HISTORY_PATH"]
    with open(log_path, "a") as ip_log:
        ip_log.write(public_ip + "\n")


def get_previous_public_ip() -> str:
    log_path = environ["IP_HISTORY_PATH"]
    try:
        with open(log_path, "r") as ip_log:
            return list(ip_log)[-1].strip()
    except FileNotFoundError:
        return ""
