import logging
import sys
from os import environ

from bot import MP2IBot
from core.logger import create_logger

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()


logger = create_logger(level=getattr(logging, environ.get("LOG_LEVEL", "INFO")))
logging.getLogger("discord").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    mp2ibot: MP2IBot = MP2IBot()

    try:
        mp2ibot.run(environ["BOT_TOKEN"], reconnect=True, log_handler=None)
    except KeyError as e:
        logger.critical(f"Missing environment variable {e}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
