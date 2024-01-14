import logging
import time
from os import environ

import public_ip
from graceful_shutdown import GracefulKiller

from dns import HandlerDNS

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

        if current_ip == previous_ip == resolved_ip:
            logging.debug("Nothing to update")
            time.sleep(300)
            continue
        elif current_ip == resolved_ip != previous_ip:
            logging.warning(
                "DNS resolves correctly but doesn't match saved Public IP.\n"
                "It was either updated externally or saving failed."
            )
            dns_handler = HandlerDNS(public_ip=current_ip)
            public_ip.save_public_ip(public_ip=current_ip)
            time.sleep(300)
            continue

        dns_handler = HandlerDNS(public_ip=current_ip)
        update_success = dns_handler.update_dns_entry()
        if update_success:
            public_ip.save_public_ip(public_ip=current_ip)
            time.sleep(600)
        else:
            logging.warning("Something bad happened. Waiting 30 minutes")
            time.sleep(1800)

    logging.info("Shutting down.")
