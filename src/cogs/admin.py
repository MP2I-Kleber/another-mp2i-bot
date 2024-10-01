"""
Admins commands. This extension should NOT be loaded on production.
Allow to dynamically reload extensions and sync the tree, to avoid restarting the bot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from discord import app_commands
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

from core._config import config
from core.personal_infos_loader import load_personal_informations

if TYPE_CHECKING:
    from discord import Interaction

    from bot import MP2IBot


logger = logging.getLogger(__name__)


class Admin(Cog):
    def __init__(self, bot: MP2IBot):
        self.bot = bot

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(config.guild_id)
    async def reload_extension(self, inter: Interaction, extension: str):
        await self.bot.reload_extension(extension)
        await inter.response.send_message(f"Extension [{extension}] reloaded successfully")

    @reload_extension.autocomplete("extension")
    async def extension_autocompleter(self, inter: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=ext, value="cogs." * (not ext.startswith("cogs.")) + ext)
            for ext in config.loaded_extensions
            if ext.startswith(current)
        ]

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(config.guild_id)
    async def sync_tree(self, inter: Interaction):
        await inter.response.defer()
        await self.bot.sync_tree()
        await inter.edit_original_response(content="Tree successfully synchronized.")

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(config.guild_id)
    @app_commands.choices(
        target=[app_commands.Choice(name=k, value=k) for k in ["colloscope", "personal_informations"]]
    )
    async def reload_data(self, inter: Interaction, target: Literal["colloscope", "personal_informations"]):
        match target:
            case "colloscope":
                await inter.response.send_message(
                    "To reload the colloscope, you need to reload the colloscope_helper extension using /reload_extension.\n"
                    "If the classes aren't updated, you may also need to use the sync_tree command."
                )

            case "personal_informations":
                try:
                    loaded = load_personal_informations()
                except Exception as e:
                    await inter.response.send_message(
                        f"Reloading the personal informations failed with the following message :\n{e}"
                    )
                else:
                    self.bot.personal_informations = loaded
                    await inter.response.send_message(
                        "Personal informations reloaded with success (check the log to be sure)."
                    )


async def setup(bot: MP2IBot):
    await bot.add_cog(Admin(bot))
