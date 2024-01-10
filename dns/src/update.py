import logging
import os

from public_ip import PublicIP

from dns import HandlerDNS


def get_config() -> dict:
    return {
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "IP_HISTORY_PATH": os.getenv("IP_HISTORY_PATH", "/logs/public_ip_history"),
        # "DNS_TEMPLATE_PATH": os.getenv("DNS_TEMPLATE_PATH", "/config/payload_template.json"),
        # "DNS_USERNAME": os.environ["DNS_USERNAME"],
        # "DNS_PASSWORD": os.environ["DNS_PASSWORD"],
        # "DNS_DEVICE_TOKEN": os.environ["DNS_DEVICE_TOKEN"],
    }


config = get_config()

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    encoding='utf-8',
    level=config["LOG_LEVEL"]
)

logging.debug(f"Config: {config}")

ip_handler = PublicIP(config)

current_ip = ip_handler.get_public_ip()
previous_ip = ip_handler.get_previous_public_ip()

if current_ip == previous_ip:
    logging.info("IP Address unchanged")
    quit(0)
else:
    logging.error("IP Address changed. Please update manually")
    quit(1)

# dns_handler = HandlerDNS(config=config)
#
# payload = dns_handler.get_payload(public_ip=current_ip)
# update_dns_status = dns_handler.update_dns_entry(payload=payload)
#
# logging.info(f"Updated DNS record. PublicIP: {current_ip}")
# logging.debug(update_dns_status)
# ip_handler.save_public_ip(public_ip=current_ip)
