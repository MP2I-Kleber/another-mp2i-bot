from __future__ import annotations

from glob import glob
from os import path
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

from utils.constants import GUILD_ID
from utils.openweathermap_api import get_weather

if TYPE_CHECKING:
    from bot import MP2IBot
    from utils.openweathermap_api.models import WeatherResponse


LAT, LON = 48.59430090208588, 7.756978617599214


class WeatherIcon(Cog):
    def __init__(self, bot: MP2IBot) -> None:
        self.bot = bot
        self.current_weather: None | WeatherResponse = None

        self.icons: dict[str, bytes] = {}
        for file_path in glob("assets/imgs/weather_icons/*.png"):
            with open(file_path, "rb") as file:
                self.icons[path.splitext(path.basename(file_path))[0]] = file.read()

        self.update_weather.start()

    async def cog_load(self) -> None:
        self.mp2i_guild = await self.bot.fetch_guild(GUILD_ID)

    @tasks.loop(hours=1)
    async def update_weather(self) -> None:
        new_weather = await get_weather((LAT, LON))
        if (
            self.current_weather is None
            or new_weather["weather"][0]["icon"] != self.current_weather["weather"][0]["icon"]
        ):
            await self.update_icon(new_weather["weather"][0]["icon"])
        self.current_weather = new_weather

    async def update_icon(self, icon: str) -> None:
        bytes_icon = self.icons.get(icon, self.icons["01d"])
        await self.mp2i_guild.edit(icon=bytes_icon)


async def setup(bot: MP2IBot):
    await bot.add_cog(WeatherIcon(bot))
