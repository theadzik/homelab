import json
from public_ip import get_public_ip
import dns


def get_config(config_path: str) -> dict:
    with open(config_path, "r") as config_file:
        return json.load(config_file)


public_ip = get_public_ip()
config = get_config("../config/secrets.json")

dns_token = dns.get_dns_token(
    username=config["username"],
    password=config["password"],
    device_token=config["device_token"]
)

for entry in config["records"]:
    payload = dns.get_payload(
        template_path="../config/payload_template.json",
        public_ip=public_ip, record_id=entry["id"],
    )
    update_dns_status = dns.update_dns_entry(
        bearer_token=dns_token,
        device_token=config["device_token"],
        payload=payload,
    )
    print(update_dns_status)
