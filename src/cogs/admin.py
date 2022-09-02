from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

from utils.constants import GUILD_ID

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
            for ext in self.bot.extensions_names
            if ext.startswith(current)
        ]


async def setup(bot: MP2IBot):
    await bot.add_cog(CTS(bot))
