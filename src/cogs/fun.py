from __future__ import annotations

import datetime as dt
import json
import os
import random
from typing import TYPE_CHECKING, cast

from discord import HTTPException, Member
from discord.app_commands import command, guild_only
from discord.ext import tasks
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

from utils import get_first_and_last_names
from utils.constants import GUILD_ID

if TYPE_CHECKING:
    from discord import Interaction, Message, TextChannel

    from bot import MP2IBot


class ValentinReact(Cog):
    def __init__(self, bot: MP2IBot) -> None:
        self.bot = bot

        self.users_reactions = {
            726867561924263946: ["🕳️"],
            1015216092920168478: ["🏳‍🌈"],
            433713351592247299: ["🩴"],
            199545535017779200: ["🪜"],
            823477539167141930: ["🥇"],
            533272313588613132: ["🥕"],
            777852203414454273: ["🐀"],
        }

        raw_birthdates: dict[str, str]
        if os.path.exists("./data/birthdates.json"):
            with open("./data/birthdates.json", "r") as f:
                raw_birthdates = json.load(f)
        else:
            raw_birthdates = {}

        self.birthdates: dict[int, dt.datetime] = {
            bot.names_to_ids[get_first_and_last_names(name)]: dt.datetime.strptime(date, r"%d-%m-%Y")
            for name, date in raw_birthdates.items()
        }

    async def cog_load(self) -> None:
        self.general_channel = cast(TextChannel, await self.bot.fetch_channel(1015172827650998352))

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != GUILD_ID:
            return

        if "cqfd" in message.content.lower():
            try:
                await message.add_reaction("<:prof:1015373456159805440>")
            except HTTPException:
                pass

        if "tu veux te battre" in message.content.lower() or "vous voulez vous battre" in message.content.lower():
            try:
                await message.add_reaction("⭕")
                await message.add_reaction("🇺")
                await message.add_reaction("🇮")
            except HTTPException:
                pass

        reactions = self.users_reactions.get(message.author.id)
        if not reactions:
            return

        reaction = random.choice(reactions)

        if random.randint(0, 25) == 0:
            try:
                await message.add_reaction(reaction)
            except HTTPException:
                pass

    @command()
    @guild_only()
    async def ratio(self, inter: Interaction, user: Member) -> None:
        tmp: list[Message] = [m async for m in user.history(limit=1)]
        message: Message | None = tmp[0] if tmp else None

        await inter.response.send_message(
            "Le ratio est à utiliser avec modération. (Je te le présenterais à l'occasion).", ephemeral=True
        )
        if message:
            response = await message.reply("RATIO!")
            await response.add_reaction("💟")

    @tasks.loop(time=dt.time(hour=7))
    async def birthday(self) -> None:
        for user_id, birthday in self.birthdates.items():
            if birthday.month == dt.datetime.now().month and birthday.day == dt.datetime.now().day:
                await self.general_channel.send(f"Joyeux anniversaire <@{user_id}> !")


async def setup(bot: MP2IBot):
    await bot.add_cog(ValentinReact(bot))
