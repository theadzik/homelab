import logging
import os
import socket
import time

import requests

MAX_BACKOFF_TIME = 300


def get_public_ip() -> str:
    remote_ip_detection_hosts = [
        "https://ifconfig.me",
        "https://ipinfo.io/ip",
        "https://ipecho.net/plain",
        "http://ip1.dynupdate.no-ip.com",
    ]
    for idx, ip_url in enumerate(remote_ip_detection_hosts):
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
        except requests.exceptions.ConnectionError:
            logging.warning(
                f"Failed do get IP from {ip_url}. No internet connection?"
            )
            if idx < len(remote_ip_detection_hosts) - 1:
                sleep_time = min(MAX_BACKOFF_TIME, 10 ** (idx + 1))  # 10, 100, 300, 300...
                logging.debug(
                    f"Waiting for {sleep_time} seconds."
                )
                time.sleep(sleep_time)
        except Exception as e:
            logging.error(
                f"Failed do get IP from {ip_url}.\n"
                f"{e}"
            )
    else:
        raise Exception(f"Failed to get public IP after {len(remote_ip_detection_hosts)} retries.")


def save_public_ip(public_ip: str) -> None:
    log_path = os.environ["IP_HISTORY_PATH"]
    with open(log_path, "a") as ip_log:
        ip_log.write(public_ip + "\n")
    logging.info(f"Saved {public_ip} IP to the history file")


def get_previous_public_ip() -> str:
    log_path = os.environ["IP_HISTORY_PATH"]
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
    logging.debug(f"{hostname} resolved to {resolved_ip}")
    return resolved_ip
