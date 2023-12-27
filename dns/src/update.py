import json
from public_ip import get_public_ip
import dns
import logging


def get_config(config_path: str) -> dict:
    with open(config_path, "r") as config_file:
        return json.load(config_file)


secrets = get_config("../config/secrets.json")
config = get_config("../config/config.json")

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    # filename='../logs/log',
    encoding='utf-8',
    level=config["log_level"]
)

public_ip = get_public_ip()

dns_token = dns.get_dns_token(
    username=secrets["username"],
    password=secrets["password"],
    device_token=secrets["device_token"]
)

for entry in config["records"]:
    payload = dns.get_payload(
        template_path="../config/payload_template.json",
        public_ip=public_ip, record_id=entry["id"],
    )
    update_dns_status = dns.update_dns_entry(
        bearer_token=dns_token,
        device_token=secrets["device_token"],
        payload=payload,
    )
    logging.info("Updated DNS record.")
    logging.debug(update_dns_status)
