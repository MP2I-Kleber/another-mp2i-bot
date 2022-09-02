import logging
from enum import Enum, auto
from typing import TypedDict

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
