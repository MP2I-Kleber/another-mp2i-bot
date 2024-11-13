from __future__ import annotations

import asyncio
import datetime as dt
from functools import partial
from typing import TYPE_CHECKING, Any, Self, cast
from zoneinfo import ZoneInfo

import discord
from discord import TextChannel, ui
from discord.app_commands import command, guild_only
from discord.ext import tasks
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from discord import Interaction, Message

    from bot import MP2IBot


class Birthday(Cog):
    def __init__(self, bot: MP2IBot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.general_channel = cast(TextChannel, await self.bot.fetch_channel(self.bot.config.birthday_channel_id))
        self.birthday.start()

        async def task() -> None:
            await self.bot.wait_until_ready()
            await self.birthday()

        def clean_task(t: asyncio.Task[Any]):
            self.init_task = None

        self.init_task = asyncio.create_task(task())
        self.init_task.add_done_callback(clean_task)

    async def cog_unload(self) -> None:
        self.birthday.stop()

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if self.is_birthday(message.author.id):  # add 🎉 reaction if birthday
            await message.add_reaction("🎉")

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

        if not inter.guild or inter.guild.id != self.bot.config.guild_id:
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

    # MAYBE: aggregate multiple birthdates in one message ?
    @tasks.loop(time=dt.time(hour=7, tzinfo=ZoneInfo("Europe/Paris")))
    async def birthday(self) -> None:
        """At 7am, check if it's someone's birthday and send a message if it is."""
        # TODO: allow to disable mentions
        now = dt.datetime.now(tz=ZoneInfo("Europe/Paris"))

        # guild = cast(discord.Guild, self.bot.get_guild(self.bot.config.guild_id))

        for pi in self.bot.personal_informations:  # iter over {user_id: birthdate}
            if pi.birthdate.month == now.month and pi.birthdate.day == now.day:
                if pi.discord_id is not None:
                    # try:
                    #     member = guild.get_member(pi.discord_id) or await guild.fetch_member(pi.discord_id)
                    # except discord.NotFound:
                    #     continue

                    # current_mp2i_roles = [
                    #     1146835004144500746,  # MPI
                    #     1146835141042393100,  # MP2I
                    #     1146919905296404600,  # PSI
                    #     1146921479192199299,  # MP
                    # ]

                    # Dont spam old students with mentions,
                    # but spam (lovely) current students.
                    # if any(role.id in current_mp2i_roles for role in member.roles):
                    send_method = partial(self.general_channel.send, view=TellHappyBirthday(pi.discord_id))
                    # else:
                    # send_method = self.general_channel.send
                else:
                    send_method = self.general_channel.send

                await send_method(f"Eh ! {pi.display} a son anniversaire ! Souhaitez-le lui 🫵 !")


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


async def setup(bot: MP2IBot) -> None:
    await bot.add_cog(Birthday(bot))
