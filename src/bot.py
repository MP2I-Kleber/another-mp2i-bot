from __future__ import annotations

from sys import exit
from typing import TYPE_CHECKING, cast
import logging

import discord
from discord.ext import commands

from utils.custom_command_tree import CustomCommandTree
from utils.constants import GUILD_ID

if TYPE_CHECKING:
    from discord.app_commands import AppCommand


logger = logging.getLogger(__name__)


class MP2IBot(commands.Bot):
    tree: CustomCommandTree  # type: ignore

    def __init__(self):
        super().__init__(
            command_prefix="unimplemented",  # Maybe consider use of IntegrationBot instead of AutoShardedBot
            tree_cls=CustomCommandTree,
            member_cache_flags=discord.MemberCacheFlags.all(),
            chunk_guilds_at_startup=True,
            allowed_mentions=discord.AllowedMentions.none(),
            intents=discord.Intents.all(),
            help_command=None,
        )

        self.extensions_names: list[str] = ["cts", "admin"]

    async def setup_hook(self) -> None:
        await self.load_extensions()

        await self.sync_tree()

    async def sync_tree(self) -> None:
        for guild_id in self.tree.active_guild_ids:
            await self.tree.sync(guild=discord.Object(guild_id))
        self.app_commands: list[AppCommand] = await self.tree.sync()

    async def on_ready(self) -> None:
        bot_user = cast(discord.ClientUser, self.user)  # Bot is logged in, so it's a ClientUser

        activity = discord.Game("WIP!")
        await self.change_presence(status=discord.Status.online, activity=activity)

        tmp = self.get_guild(GUILD_ID)
        if not tmp:
            logger.critical("Support server cannot be retrieved")
            exit(1)
        self.guild = tmp

        logger.info(f"Logged in as : {bot_user.name}")
        logger.info(f"ID : {bot_user.id}")

    async def load_extensions(self) -> None:
        for ext in self.extensions_names:
            if not ext.startswith("cogs."):
                ext = "cogs." + ext

            try:
                await self.load_extension(ext)
            except commands.errors.ExtensionError as e:
                logger.error(f"Failed to load extension {ext}.", exc_info=e)
            else:
                logger.info(f"Extension {ext} loaded successfully.")
