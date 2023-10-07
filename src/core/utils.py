"""
A bunch of utilities functions used across the bot.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Any, TypedDict

import discord

logger = logging.getLogger(__name__)


class Response(TypedDict):
    embed: discord.Embed


class ResponseType(Enum):
    success = auto()
    info = auto()
    error = auto()
    warning = auto()


_embed_colors = {
    ResponseType.success: discord.Color.brand_green(),
    ResponseType.info: discord.Color.blurple(),
    ResponseType.error: discord.Color.brand_red(),
    ResponseType.warning: discord.Color.yellow(),
}

_embed_author_icon_urls = {
    ResponseType.success: "https://cdn.discordapp.com/attachments/584397334608084992/1007741457328787486/success.png",
    ResponseType.info: "https://cdn.discordapp.com/attachments/584397334608084992/1007741456708022293/info.png",
    ResponseType.error: "https://cdn.discordapp.com/attachments/584397334608084992/1007741455483281479/error.png",
    ResponseType.warning: "https://cdn.discordapp.com/attachments/584397334608084992/1007741457819516999/warning.png",
}


def response_constructor(response_type: ResponseType, message: str, embedded: bool = True) -> Response:
    embed = discord.Embed(
        color=_embed_colors[response_type],
    )

    if len(message) > 256:
        logger.warning(f'This error message is too long to be displayed in author field. "{message}"')

    embed.set_author(name=message, icon_url=_embed_author_icon_urls[response_type])

    return {"embed": embed}


def capitalize(s: str) -> str:
    """Capitalize names that contains a '-'

    Args:
        s: the string to capitalize

    Returns:
        A correctly capitalized string.

    Example:
        capitalize("charles-daniel") returns "Charles-Daniel"
    """
    return "-".join(p.capitalize() for p in s.split("-"))


class BraceMessage:
    """
    This function works as a workaround to use f-string in logger.
    Because logging is old, it uses % formatting, like logger.debug("Hello %s", "world").
    If we want to use f-string, we could do logger.debug(f"Hello {world}"), but it is not recommended, because the
    f-string will be evaluated even if the logger is not in debug mode (ie nothing is printed in the console).

    Then, because logger.log(..., obj) will call str(obj), we can use this class to wrap the f-string, and then
    we can use logger.debug(BraceMessage("Hello {world}")).

    To make it more convenient, we can import this class as __ (double underscore), and then we can do
    logger.debug(__("Hello {world}", world=world)).

    If we want it to be even more powerful, we *could* inspect the stack to get the variables from the invocation scope,
    but it is not a really recommended practice, and it is not really useful in our case.
    """

    def __init__(self, fmt: Any, /, *args: Any, **kwargs: Any):
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return self.fmt.format(*self.args, **self.kwargs)
