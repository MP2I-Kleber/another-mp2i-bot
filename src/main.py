import logging
import sys
from os import environ

from bot import MP2IBot
from utils.logger import create_logger

logger = create_logger(level=getattr(logging, environ.get("LOG_LEVEL", "INFO")))
logging.getLogger("discord").setLevel(logging.INFO)


def main():
    mp2ibot: MP2IBot = MP2IBot()

    try:
        mp2ibot.run(environ["BOT_TOKEN"], reconnect=True, log_handler=None)
    except KeyError as e:
        logger.critical(f"Missing environment variable {e}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
