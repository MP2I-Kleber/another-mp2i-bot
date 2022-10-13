from __future__ import annotations

import logging
import re
from enum import Enum, auto
from typing import NamedTuple, TypedDict

import discord

FIRST_LAST_NAME = re.compile(r"([A-ZÀ-ß\- ]*) ((?:[A-Z][a-zà-ÿ]+|\-| )+)")

logger = logging.getLogger(__name__)


class Name(NamedTuple):
    first: str
    last: str


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


def get_first_and_last_names(name: str) -> Name:
    match = FIRST_LAST_NAME.match(name)
    if not match:
        raise ValueError("First and last name not found")
    return Name(last=match.group(1), first=match.group(2))
