"""
This cog will check the restauration page of the school website, and post the menu on Discord.
"""

from __future__ import annotations

import io
import json
from os import path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import httpx
from bs4 import BeautifulSoup, Tag
from discord import File, HTTPException, TextChannel
from discord.ext import tasks
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from bot import MP2IBot

RESTAURATION_PATH = "./data/restauration.json"


class Restauration(Cog):
    def __init__(self, bot: MP2IBot) -> None:
        self.bot = bot

        self.already_posted: list[str] = self.read_restauration_file()

    async def cog_load(self) -> None:
        await self.check_menu()
        self.check_menu.start()

    async def cog_unload(self) -> None:
        self.check_menu.stop()

    def add_restauration_file(self, filename: str) -> None:
        """A utility function to register what menu file has already been sent

        In a beautiful world, we should use a database such as sqlite3.
        Maybe I will improve this on day.. or could you ?
        Not an excessive work.

        Args:
            filename: the filename of the menu image
        """
        self.already_posted.append(filename)
        with open(RESTAURATION_PATH, "w") as f:
            json.dump(self.already_posted, f)

    def read_restauration_file(self) -> list[str]:
        """A utility function to get the list of what menu file has already been sent.

        Returns:
            The list of menu images filenames.
        """
        if not path.exists(RESTAURATION_PATH):
            with open(RESTAURATION_PATH, "w") as f:
                json.dump([], f)
            return []
        with open(RESTAURATION_PATH, "r") as f:
            return json.load(f)


    @tasks.loop(minutes=60)
    async def check_menu(self) -> None:
        async with httpx.AsyncClient() as client:
            result = await client.get("https://lycee-kleber.com.fr/restauration")
            page = result.text

        scrap = BeautifulSoup(page, "html.parser")
        img_link = scrap.body.div.div.div.section[3].div.div.div.div.div.div[3].div.div.h2[2].strong.a.get('href')


        if img_link in self.already_posted:
            return
        else:
            self.add_restauration_file(img_link)

        channels: list[TextChannel] = [
            ch for ch in self.bot.get_all_channels() if isinstance(ch, TextChannel) and ch.name == "menu-cantine"
        ]

        for channel in channels:
            try:
                await channel.send(img_link)
            except HTTPException:
                pass

async def setup(bot: MP2IBot):
    await bot.add_cog(Restauration(bot))
