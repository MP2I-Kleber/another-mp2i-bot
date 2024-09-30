"""
Config informations should always be retrieved from bot.config, this ensure that the config has been overwritten if
needed. Otherwise, if the config is used before the invocation of main() from main.py, config informations are not set
correctly.
A warning should be raised if we try to access config while it is not defined.
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any, ClassVar, Self

logger = logging.getLogger(__name__)

MANDATORY: Any = object()


class Config:
    """Get any configuration information from here.

    This class is a singleton. You can get the configurations info from `bot.config`, or import the instance `config`
    from this module, or even use `Config()` as they are all the same instance.

    To ensure the config keys are accessed after being defined, the `define_config` function should be called when the
    config is ready to be used. This will set the `_defined` attribute to True, and any access to the config before this
    will raise a warning.

    The values assigned bellow are the default values, and can be overwritten by the `define_config` function.
    Everything present in the `config.toml` file will be added to the config instance (even if it is not defined here).
    But please make sure to define the config keys here, for autocompletion.

    Refer to [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) for more information.
    """

    guild_id: ClassVar[int] = MANDATORY
    birthday_channel_id: ClassVar[int] = MANDATORY
    loaded_extensions: ClassVar[list[str]] = [
        "weather_icon",
        "cts",
        "restauration",
        "fun",
        "mp2i",
        "openai_chatbot",
        "colloscope_helper",
    ]

    _instance: ClassVar[Self] | None = None
    _defined: ClassVar[bool] = False

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def define_config(cls, config_path: Path | str | None = None, **kwargs: Any):
        if config_path:
            with open(config_path, "rb") as f:
                kwargs |= tomllib.load(f)

        cls(**kwargs)  # it is a singleton, so it will directly affect the instance.

        # We declare config = Config() at the end of the file (to simplify the access of the config), so
        # Config._instance is already defined. We need another method to check if the config is already defined when
        # accessing its attributes. This is the role of Config._defined.
        Config._defined = True

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getattribute__(self, name: str) -> Any:
        if name in ("__init__"):
            return super().__getattribute__(name)

        if Config._defined is False:
            logger.warning("Config accessed before being defined.", extra={"ignore_discord": True})

        try:
            return super().__getattribute__(name)
        except AttributeError:
            return None


config = Config()
