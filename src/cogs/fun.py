"""
This is a chaotic cog, regrouping all sort of fun commands.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import random
from functools import partial
from typing import TYPE_CHECKING, Any, Self, cast
from zoneinfo import ZoneInfo

import discord
from discord import AllowedMentions, HTTPException, Member, TextChannel, ui
from discord.app_commands import command, describe, guild_only
from discord.ext import tasks
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

from core.constants import GUILD_ID, MAIN_CHANNEL_ID

if TYPE_CHECKING:
    from discord import Interaction, Message

    from bot import FISABot


class Fun(Cog):
    def __init__(self, bot: FISABot) -> None:
        self.bot = bot

        # Because of *important*: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        self.task_reference: asyncio.Task[Any] | None = None

        # reactions that can be randomly added under these users messages.
        self.users_reactions: dict[int, list[str]] = {}
        # words that trigger the bot to react with a random emoji from the list assigned to the user.
        self.users_triggers: dict[int, list[str]] = {}

    async def cog_load(self) -> None:
        self.general_channel = cast(TextChannel, await self.bot.fetch_channel(MAIN_CHANNEL_ID))
        self.birthday.start()

        async def task() -> None:
            await self.bot.wait_until_ready()
            await self.birthday()

        def clean_task(task: asyncio.Task[Any]):
            self.task_reference = None

        self.task_reference = asyncio.create_task(task())
        self.task_reference.add_done_callback(clean_task)

    async def cog_unload(self) -> None:
        self.birthday.stop()

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != GUILD_ID:  # only works into the MP2I guild.
            return
        if message.author.id == message.guild.me.id:
            return

        if self.is_birthday(message.author.id):  # add 🎉 reaction if birthday
            await message.add_reaction("🎉")

        # if "cqfd" in message.content.lower():  # add reaction if "cqfd" in message
        #     await message.add_reaction("<:prof:1015373456159805440>")

        reactions = self.users_reactions.get(message.author.id)
        if reactions:
            reaction = random.choice(reactions)  # noqa: S311

            # react randomly or if message contains a trigger word
            triggers = self.users_triggers[message.author.id]
            if random.randint(0, 25) == 0 or any(e in message.content.lower() for e in triggers):  # noqa: S311
                await message.add_reaction(reaction)

    def is_birthday(self, user_id: int) -> bool:
        """Tell if a user has birthday or not.

        Args:
            user_id (int): the user to check

        Returns:
            bool: also return False if the birthdate is unknown.
        """
        personal_info = self.bot.get_personal_information(user_id)
        if personal_info is None:
            return False
        birthdate = personal_info.birthdate

        now = dt.datetime.now(tz=ZoneInfo("Europe/Paris"))
        return birthdate.day == now.day and birthdate.month == now.month

    @command()
    @guild_only()
    async def prochains_anniversaires(self, inter: Interaction) -> None:
        if not isinstance(inter.channel, discord.abc.Messageable):
            return

        if not inter.guild or inter.guild.id != GUILD_ID:
            return

        rows: list[str] = []
        now = dt.datetime.now()

        def sorted_key(date: dt.datetime) -> tuple[bool, dt.datetime]:
            passed = date.replace(year=now.year).timestamp() - now.timestamp() < 0
            relative = date.replace(year=now.year + 1) if passed else date.replace(year=now.year)

            return passed, relative

        for pi in sorted(self.bot.personal_informations, key=lambda pi: sorted_key(pi.birthdate)):
            ts: int = int(pi.birthdate.timestamp())
            relative = sorted_key(pi.birthdate)[1]

            line = f"{pi.display} ({pi.origin}). <t:{ts}:D> (<t:{int(relative.timestamp())}:R>)"
            if sum(len(row) + 1 for row in rows) > 4000:
                break
            rows.append(line)

        embed = discord.Embed(title="Listes des prochains anniversaires", description="\n".join(rows))
        await inter.response.send_message(embed=embed)

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

    # MAYBE: aggregate multiple birthdates in one message ?
    @tasks.loop(time=dt.time(hour=7, tzinfo=ZoneInfo("Europe/Paris")))
    async def birthday(self) -> None:
        """At 7am, check if it's someone's birthday and send a message if it is."""
        now = dt.datetime.now(tz=ZoneInfo("Europe/Paris"))

        for pi in self.bot.personal_informations:  # iter over {user_id: birthdate}
            if pi.birthdate.month == now.month and pi.birthdate.day == now.day:
                if pi.discord_id is not None:
                    send_method = partial(
                        self.general_channel.send,
                        view=TellHappyBirthday(pi.discord_id),
                    )
                else:
                    send_method = self.general_channel.send

                await send_method(f"Eh ! {pi.display} a anniversaire ! Souhaitez-le lui !")


class TellHappyBirthday(ui.View):
    """A view with a single button to tell a user happy birthday (with mention <3).


    Args:
        user_id (int): the user who had birthday !
    """

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        # Prevents users from wishing happy birthdays late by disabling interactions after 17 hours (in seconds),
        # the message being sent at 7 AM.
        super().__init__(timeout=17 * 60 * 60)

    @ui.button(label="Happy Birthday !", emoji="🎉")
    async def tell_happy_birthday(self, inter: Interaction, button: ui.Button[Self]) -> None:
        mentions = discord.AllowedMentions(
            users=True,
        )
        await inter.response.send_message(
            f"{inter.user.display_name} souhaite un joyeux anniversaire à <@{self.user_id}> !",
            allowed_mentions=mentions,
        )


async def setup(bot: FISABot) -> None:
    await bot.add_cog(Fun(bot))
