"""
A custom CommandTree, it only allow to handle errors in a more convenient way.
Every time a interaction command fails, the error is retrieved and managed here.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from discord.app_commands import CommandNotFound, CommandTree

from .errors import BaseError
from .utils import ResponseType, response_constructor

if TYPE_CHECKING:
    from discord import Interaction, Invite
    from discord.app_commands import AppCommandError

    from bot import MP2IBot


logger = logging.getLogger(__name__)


class CustomCommandTree(CommandTree["MP2IBot"]):
    def __init__(self, *args: Any, **kwargs: Any):
        self._invite: Invite | None = None
        super().__init__(*args, **kwargs)

    @property
    def active_guild_ids(self) -> set[int]:
        return self._guild_commands.keys() | {g for _, g, _ in self._context_menus if g is not None}  # type: ignore

    async def send_error(self, inter: Interaction, error_message: str) -> None:
        """A function to send an error message."""
        strategy = inter.response.send_message
        if inter.response.is_done():
            strategy = inter.followup.send
        await strategy(**response_constructor(ResponseType.error, error_message), ephemeral=True)

    async def on_error(self, interaction: Interaction, error: AppCommandError) -> None:
        """Function called when a command raise an error."""

        match error:
            case CommandNotFound():
                return
            case BaseError():
                return await self.send_error(interaction, str(error))
            case _:
                await self.send_error(interaction, f"Une erreur random est survenue j'ai pas capté sorry.\n{error}")

        logger.error(f"An unhandled error happened : {error} ({type(error)})")
