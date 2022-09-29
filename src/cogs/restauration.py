from __future__ import annotations

import io
import json
from os import path
from typing import TYPE_CHECKING, cast
from zipfile import ZipFile

import httpx
from bs4 import BeautifulSoup, Tag
from discord import File, TextChannel
from discord.ext import tasks
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

from utils.constants import RESTAURATION_CHANNEL_ID

if TYPE_CHECKING:
    from bot import MP2IBot

RESTAURATION_PATH = "./data/restauration.json"


class Restauration(Cog):
    def __init__(self, bot: MP2IBot) -> None:
        self.bot = bot
        self.check_menu.start()

        self.already_posted: list[str] = self.read_restauration_file()

    async def cog_load(self) -> None:
        self.restauration_channel = cast(TextChannel, await self.bot.fetch_channel(RESTAURATION_CHANNEL_ID))

    async def cog_unload(self) -> None:
        self.check_menu.stop()

    def add_restauration_file(self, filename: str) -> None:
        self.already_posted.append(filename)
        with open(RESTAURATION_PATH, "w") as f:
            json.dump(self.already_posted, f)

    def read_restauration_file(self) -> list[str]:
        if not path.exists(RESTAURATION_PATH):
            with open(RESTAURATION_PATH, "w") as f:
                json.dump([], f)
            return []
        with open(RESTAURATION_PATH, "r") as f:
            return json.load(f)

    async def get_menu_imgs(self) -> dict[str, io.BytesIO]:
        async with httpx.AsyncClient() as client:
            result = await client.get("https://lyc-kleber.monbureaunumerique.fr/l-etablissement/restaurant-scolaire/")
            page = result.text

            scrap = BeautifulSoup(page, "html.parser")

            if not isinstance(tag := scrap.find("input", id="ID_METATAG"), Tag):
                raise Exception("Could not find the tag")
            if not isinstance(tag_id := tag.get("value"), str):
                raise Exception("Could not find the tag id")

            result = await client.get(
                f"https://lyc-kleber.monbureaunumerique.fr/exportContent?&ACTION=EXPORTER&exportType=FICHE&ID_FICHE={tag_id}"
            )
            zip_buffer = io.BytesIO(result.read())
            zip_obj = ZipFile(zip_buffer, "r")

            imgs_buffers: dict[str, io.BytesIO] = {}
            imgs = [obj for obj in zip_obj.infolist() if obj.filename.endswith("jpeg") and obj.file_size > 50_000]

            for img in imgs:
                buffer = io.BytesIO(zip_obj.read(img.filename))
                buffer.seek(0)
                imgs_buffers[img.filename] = buffer

            return imgs_buffers

    @tasks.loop(hours=3)
    async def check_menu(self) -> None:
        try:
            menus = await self.get_menu_imgs()
        except Exception:
            return

        for menu, img in menus.items():
            if menu not in self.already_posted:
                self.add_restauration_file(menu)
                await self.restauration_channel.send(file=File(img, menu))


async def setup(bot: MP2IBot):
    await bot.add_cog(Restauration(bot))
