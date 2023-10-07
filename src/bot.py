from __future__ import annotations

import logging
from sys import exit
from typing import TYPE_CHECKING, cast

import discord
from discord.ext import commands

from core.constants import GUILD_ID
from core.custom_command_tree import CustomCommandTree
from core.personal_infos_loader import PersonalInformation, load_personal_informations
from core.utils import BraceMessage as __

if TYPE_CHECKING:
    from discord.app_commands import AppCommand


logger = logging.getLogger(__name__)


class MP2IBot(commands.Bot):
    tree: CustomCommandTree  # type: ignore

    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            tree_cls=CustomCommandTree,
            member_cache_flags=discord.MemberCacheFlags.all(),
            chunk_guilds_at_startup=True,
            allowed_mentions=discord.AllowedMentions.none(),
            intents=discord.Intents.all(),
            help_command=None,
        )

        self.extensions_names: list[str] = ["weather_icon", "cts", "restauration", "fun", "mp2i"]
        self.personal_informations: list[PersonalInformation] = load_personal_informations()

    def get_personal_information(self, discord_id: int) -> PersonalInformation | None:
        """Return a object containing personal informations about a user.

        Args:
            discord_id: the discord id of the user

        Returns:
            PersonalInformation: the object containing personal informations about the user
        """
        return discord.utils.get(self.personal_informations, discord_id=discord_id)

    async def setup_hook(self) -> None:
        try:
            self.guild = await self.fetch_guild(GUILD_ID)
        except discord.Forbidden:
            logger.critical("Support server cannot be retrieved, check the GUILD_ID constant.")
            exit(1)

        await self.load_extensions()
        await self.sync_tree()

    async def sync_tree(self) -> None:
        for guild_id in self.tree.active_guild_ids:
            await self.tree.sync(guild=discord.Object(guild_id))
        self.app_commands: list[AppCommand] = await self.tree.sync()

    async def on_ready(self) -> None:
        bot_user = cast(discord.ClientUser, self.user)  # Bot is logged in, so it's a ClientUser

        activity = discord.Game("BLUFF!")
        await self.change_presence(status=discord.Status.online, activity=activity)

        logger.info(f"Logged in as : {bot_user.name}")
        logger.info(f"ID : {bot_user.id}")

    async def load_extensions(self) -> None:
        for ext in self.extensions_names:
            if not ext.startswith("cogs."):
                ext = "cogs." + ext

            try:
                await self.load_extension(ext)
            except commands.errors.ExtensionError as e:
                logger.error(__("Failed to load extension {}.", ext), exc_info=e)
            else:
                logger.info(__("Extension {} loaded successfully.", ext))
