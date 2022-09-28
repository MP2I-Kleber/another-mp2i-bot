from __future__ import annotations

import random
from typing import TYPE_CHECKING

from discord import HTTPException
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

from utils.constants import GUILD_ID

if TYPE_CHECKING:
    from discord import Message

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

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != GUILD_ID:
            return

        if "cqfd" in message.content.lower():
            try:
                await message.add_reaction("<:prof:1015373456159805440>")
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


async def setup(bot: MP2IBot):
    await bot.add_cog(ValentinReact(bot))
