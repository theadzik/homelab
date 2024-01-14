import logging
import os
import platform
import signal
import smtplib
from base64 import b64encode
from email.message import EmailMessage

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
                self.send_error_email(status_code=response.status_code, response_text=response.text)
                logging.warning("Waiting indefinitely.")
                signal.pause()
            case "911":
                logging.warning(f"Failed to update DNS: [{response.status_code}] {response.text}")
            case _:
                logging.error(f"Did not understand response: [{response.status_code}] {response.text}")
        return False

    def send_error_email(self, status_code: int, response_text: str):
        message = EmailMessage()
        message.set_content(
            f"We failed to update your DNS entries."
            f"Public IP: {self.public_ip}"
            f"Response: [{status_code}] {response_text}"
        )
        message['Subject'] = f"[DDNS] Failed to update IP ({response_text})"
        message['From'] = os.environ["SMTP_USERNAME"]
        message['To'] = os.environ["MAINTAINER_EMAIL"]

        mailer = smtplib.SMTP_SSL(host=os.environ["SMTP_HOST"], port=os.environ["SMTP_PORT"])
        mailer.login(user=os.environ["SMTP_USERNAME"], password=os.environ["SMTP_PASSWORD"])
        mailer.send_message(msg=message)
        logging.info(f"Sent an email to {message['To']}")
