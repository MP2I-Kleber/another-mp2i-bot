"""
Admins commands. This extension should NOT be loaded on production.
Allow to dynamically reload extensions and sync the tree, to avoid restarting the bot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

from core.constants import GUILD_ID, LOADED_EXTENSIONS

if TYPE_CHECKING:
    from discord import Interaction

    from bot import MP2IBot


logger = logging.getLogger(__name__)


class CTS(Cog):  # TODO: add checkers
    def __init__(self, bot: MP2IBot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guilds(GUILD_ID)
    async def reload_extension(self, inter: Interaction, extension: str):
        await self.bot.reload_extension(extension)
        await inter.response.send_message(f"Extension [{extension}] reloaded successfully")

    @reload_extension.autocomplete("extension")
    async def extension_autocompleter(self, inter: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=ext, value="cogs." * (not ext.startswith("cogs.")) + ext)
            for ext in LOADED_EXTENSIONS
            if ext.startswith(current)
        ]

    @app_commands.command()
    @app_commands.guilds(GUILD_ID)
    async def sync_tree(self, inter: Interaction):
        await inter.response.defer()
        await self.bot.sync_tree()
        await inter.edit_original_response(content="Tree successfully synchronized.")


async def setup(bot: MP2IBot):
    await bot.add_cog(CTS(bot))
