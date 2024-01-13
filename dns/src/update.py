import logging
import time
from os import environ

import public_ip
from graceful_shutdown import GracefulKiller

from dns import HandlerDNS

# TODO: Add no-ip response handling https://www.noip.com/integrate/response
# TODO: Add sending email on selected responses from no-ip

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    encoding='utf-8',
    level=environ["LOG_LEVEL"]
)

if __name__ == '__main__':
    killer = GracefulKiller()
    while not killer.kill_now:
        current_ip = public_ip.get_public_ip()
        previous_ip = public_ip.get_previous_public_ip()
        resolved_ip = public_ip.resolve_dns(environ["HOSTNAME"])

        if not (current_ip == previous_ip == resolved_ip):
            dns_handler = HandlerDNS(public_ip=current_ip)
            dns_handler.update_dns_entry()
            public_ip.save_public_ip(public_ip=current_ip)
            time.sleep(600) # Allow extra time for TTL to pass
        else:
            logging.debug("IP Address unchanged")

        time.sleep(300)

    logging.info("Shutting down.")
