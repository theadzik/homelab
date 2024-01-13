import logging
from os import environ

import public_ip

from dns import HandlerDNS

# TODO: Change into service running constantly
# TODO: Add no-ip response handling https://www.noip.com/integrate/response
# TODO: Add sending email on selected responses from no-ip

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    encoding='utf-8',
    level=environ["LOG_LEVEL"]
)

current_ip = public_ip.get_public_ip()
previous_ip = public_ip.get_previous_public_ip()
resolved_ip = public_ip.resolve_dns(environ["HOSTNAME"])

if current_ip == previous_ip == resolved_ip:
    logging.info("IP Address unchanged")
    quit(0)

dns_handler = HandlerDNS(public_ip=current_ip)
dns_handler.update_dns_entry()
public_ip.save_public_ip(public_ip=current_ip)
