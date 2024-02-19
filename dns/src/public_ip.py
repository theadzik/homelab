import logging
import socket
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
        try:
            public_ip = requests.request("GET", ip_url)
            public_ip.raise_for_status()
            logging.debug(f"Current Public IP: {public_ip.text}")
            return public_ip.text
        except requests.HTTPError:
            logging.warning(
                f"Failed do get IP from {ip_url}.\n"
                f"Status code: {public_ip.status_code}\n"
                f"Response: {public_ip.text}"
            )
        except Exception as e:
            logging.warning(
                f"Failed do get IP from {ip_url}.\n"
                f"{e}"
            )
    else:
        raise Exception(f"Failed to get public IP after {len(remote_ip_detection_hosts)} retries.")


def save_public_ip(public_ip: str) -> None:
    log_path = environ["IP_HISTORY_PATH"]
    with open(log_path, "a") as ip_log:
        ip_log.write(public_ip + "\n")
    logging.debug("Saved new public IP to file")


def get_previous_public_ip() -> str:
    log_path = environ["IP_HISTORY_PATH"]
    try:
        with open(log_path, "r") as ip_log:
            previous_ip = list(ip_log)[-1].strip()
            logging.debug(f"Previous IP: {previous_ip}")
            return previous_ip
    except FileNotFoundError:
        logging.warning("No previous IP found")
        return ""


def resolve_dns(hostname: str) -> str:
    resolved_ip = socket.gethostbyname(hostname)
    logging.info(f"{hostname} resolved to {resolved_ip}")
    return resolved_ip
