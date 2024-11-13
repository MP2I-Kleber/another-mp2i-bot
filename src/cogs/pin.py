from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Message, app_commands
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from discord import Interaction

    from bot import MP2IBot


class Pin(Cog):
    def __init__(self, bot: MP2IBot) -> None:
        self.bot = bot

        self.bot.tree.add_command(
            app_commands.ContextMenu(
                name="Epingler/Desepingler",
                callback=self.pin,
            )
        )

    async def pin(self, interaction: Interaction, message: Message):
        if message.pinned:
            await message.unpin()
            await interaction.response.send_message(f"Message {message.jump_url} désépinglé.", ephemeral=True)
        else:
            await message.pin()
            await interaction.response.send_message(f"Message {message.jump_url} épinglé.", ephemeral=True)


async def setup(bot: MP2IBot) -> None:
    await bot.add_cog(Pin(bot))
