from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from discord import Message

    from bot import MP2IBot


class ValentinReact(Cog):
    def __init__(self, bot: MP2IBot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != 1015136740127821885:
            return
        if message.author.id == 726867561924263946:
            await message.add_reaction("🕳️")


async def setup(bot: MP2IBot):
    await bot.add_cog(ValentinReact(bot))
