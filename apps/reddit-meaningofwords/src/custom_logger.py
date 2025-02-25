import logging
import os
import sys

logging.basicConfig(encoding="utf-8", level=logging.WARNING, stream=sys.stdout)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(os.getenv("LOG_LEVEL", logging.INFO))

    return logger
