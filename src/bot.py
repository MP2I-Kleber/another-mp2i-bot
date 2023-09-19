from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from glob import glob
from sys import exit
from typing import TYPE_CHECKING, cast
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands

from utils.constants import GUILD_ID
from utils.custom_command_tree import CustomCommandTree

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

        self.extensions_names: list[str] = ["weather_icon", "cts", "restauration", "fun", "mp2i"]
        self.personal_informations: list[PersonalInformation] = self.load_personal_informations()

    def load_personal_informations(self) -> list[PersonalInformation]:
        result: list[PersonalInformation] = []

        def read(filename: str):
            origin = os.path.splitext(os.path.basename(filename))[0]
            with open(csv_file, encoding="utf-8", mode="r") as f:
                for i, row in enumerate(csv.DictReader(f)):
                    try:
                        yield PersonalInformation(**row, origin=origin)
                    except ValueError as e:
                        logger.warning(f"Row {i + 1} is invalid in {origin}.csv: {e}")

        for csv_file in glob("/resources/personal_informations/*.csv"):
            if csv_file == "/resources/personal_informations/example.csv":
                continue
            result.extend(read(csv_file))

        return result

    def get_personal_information(self, discord_id: int) -> PersonalInformation | None:
        return discord.utils.get(self.personal_informations, discord_id=discord_id)

    async def setup_hook(self) -> None:
        tmp = await self.fetch_guild(GUILD_ID)
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


class PersonalInformation:
    def __init__(
        self,
        firstname: str | None,
        lastname: str | None,
        nickname: str | None,
        discord_id: str | None,
        birthdate: str,
        origin: str,
    ) -> None:
        if not any((firstname, lastname, nickname)):
            raise ValueError("At least one of firstname, lastname or nickname must be set.")
        self.firstname = firstname
        self.lastname = lastname
        self.nickname = nickname
        self.origin = origin

        if discord_id is not None:
            self.discord_id = int(discord_id)
        else:
            self.discord_id = None

        self.birthdate = datetime.strptime(birthdate, r"%d-%m-%Y").astimezone(tz=ZoneInfo("Europe/Paris"))

    @property
    def display(self):
        if self.nickname:
            return self.nickname
        assert self.firstname is not None

        parts = [self.firstname.capitalize()]
        if self.lastname:
            parts.append(f"{self.lastname.upper()[0]}.")
        return " ".join(parts)
