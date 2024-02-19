import json
import logging

from public_ip import PublicIP

import dns


def get_config(config_path: str) -> dict:
    with open(config_path, "r") as config_file:
        return json.load(config_file)


secrets = get_config("../config/secrets.json")
config = get_config("../config/config.json")

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    encoding='utf-8',
    level=config["log_level"]
)

ip_handler = PublicIP(config)

current_ip = ip_handler.get_public_ip()
previous_ip = ip_handler.get_previous_public_ip()

if current_ip == previous_ip:
    logging.info(f"IP Address unchanged")
    quit(0)

dns_token = dns.get_dns_token(
    username=secrets["username"],
    password=secrets["password"],
    device_token=secrets["device_token"]
)

for entry in config["records"]:
    payload = dns.get_payload(
        template_path="../config/payload_template.json",
        public_ip=current_ip, record_id=entry["id"],
    )
    update_dns_status = dns.update_dns_entry(
        bearer_token=dns_token,
        device_token=secrets["device_token"],
        payload=payload,
    )
    logging.info(f"Updated DNS record. EntryID: {entry['id']}. PublicIP: {current_ip}")
    logging.debug(update_dns_status)
    ip_handler.save_public_ip(public_ip=current_ip)
