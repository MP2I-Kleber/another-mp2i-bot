import logging
import sys
from os import environ
from pathlib import Path

from bot import FISABot
from core._config import Config
from core.logger import create_logger
from core.utils import BraceMessage as __

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    pass
else:
    load_dotenv()


logger = create_logger(level=getattr(logging, environ.get("LOG_LEVEL", "INFO")))
logging.getLogger("discord").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def main():
    Config.define_config(Path("./config.toml"))
    bot = FISABot()

    try:
        bot.run(environ["BOT_TOKEN"], reconnect=True, log_handler=None)
    except KeyError as e:
        logger.critical(__("Missing environment variable {}.", e))
        sys.exit(1)


if __name__ == "__main__":
    main()
