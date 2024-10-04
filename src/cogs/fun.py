# ruff: noqa: S311

"""
This is a chaotic cog, regrouping all sort of fun commands.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord import AllowedMentions, HTTPException, Member
from discord.app_commands import command, describe, guild_only
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from discord import Interaction, Message

    from bot import FISABot


class Fun(Cog):
    def __init__(self, bot: FISABot) -> None:
        self.bot = bot

        # reactions that can be randomly added under these users messages.
        self.users_reactions: dict[int, list[str]] = {}
        # words that trigger the bot to react with a random emoji from the list assigned to the user.
        self.users_triggers: dict[int, list[str]] = {}

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != self.bot.config.guild_id:  # only works into the MP2I guild.
            return
        if message.author.id == message.guild.me.id:
            return

        # if "cqfd" in message.content.lower():  # add reaction if "cqfd" in message
        #     await message.add_reaction("<:prof:1015373456159805440>")

        reactions = self.users_reactions.get(message.author.id)
        if reactions:
            reaction = random.choice(reactions)

            # react randomly or if message contains a trigger word
            triggers = self.users_triggers[message.author.id]
            if random.randint(0, 25) == 0 or any(e in message.content.lower() for e in triggers):
                await message.add_reaction(reaction)

    @command()
    @guild_only()
    @describe(
        user="L'utilisateur que vous souhaitez ratio!",
        anonymous="Si vous ne souhaitez pas que l'on qui est à l'origine cet impitoyable ratio.",
    )
    async def ratio(self, inter: Interaction, user: Member, anonymous: bool = False) -> None:
        if not isinstance(inter.channel, discord.abc.Messageable):  # only works if we can send message into the channel
            return

        # we look into previous message to locate the specific message to ratio
        message: Message | None = await discord.utils.find(
            lambda m: m.author.id == user.id, inter.channel.history(limit=100)
        )

        await inter.response.send_message(
            "Le ratio est à utiliser avec modération. (Je te le présenterais à l'occasion).",
            ephemeral=True,
        )
        if message:
            text: str = "ratio."
            if not anonymous:  # add a signature if not anonym
                text += " by " + inter.user.mention

            try:
                response = await message.reply(text, allowed_mentions=AllowedMentions.none())
                await response.add_reaction("💟")
            except HTTPException:
                pass


async def setup(bot: FISABot) -> None:
    await bot.add_cog(Fun(bot))
