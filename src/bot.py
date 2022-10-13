from __future__ import annotations

import json
import logging
import os
from sys import exit
from typing import TYPE_CHECKING, cast

import discord
from discord.ext import commands

from utils import get_first_and_last_names
from utils.constants import GUILD_ID
from utils.custom_command_tree import CustomCommandTree

if TYPE_CHECKING:
    from discord.app_commands import AppCommand

    from utils import Name


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

        raw_names_to_ids: dict[str, int]
        if os.path.exists("./data/names-to-ids.json"):
            with open("./data/names-to-ids.json", "r") as f:
                raw_names_to_ids = json.load(f)
        else:
            raw_names_to_ids = {}

        self.ids_to_names: dict[int, Name] = {
            id_: get_first_and_last_names(name) for name, id_ in raw_names_to_ids.items()
        }
        self.extensions_names: list[str] = ["weather_icon", "cts", "restauration", "fun"]

    @property
    def names_to_ids(self) -> dict[Name, int]:
        return {name: id_ for id_, name in self.ids_to_names.items()}

    async def setup_hook(self) -> None:
        tmp = self.get_guild(GUILD_ID)
        if not tmp:
            logger.critical("Support server cannot be retrieved")
            exit(1)
        self.guild = tmp

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
                logger.error(f"Failed to load extension {ext}.", exc_info=e)
            else:
                logger.info(f"Extension {ext} loaded successfully.")
