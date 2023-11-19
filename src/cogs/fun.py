"""
This is a chaotic cog, regrouping all sort of fun commands.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import random
from functools import partial
from typing import TYPE_CHECKING, cast
from zoneinfo import ZoneInfo

import discord
from discord import AllowedMentions, HTTPException, Member, TextChannel, ui
from discord.app_commands import command, describe, guild_only
from discord.ext import tasks
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]
from typing_extensions import Self

from core.constants import GUILD_ID, MAIN_CHANNEL_ID

if TYPE_CHECKING:
    from discord import Interaction, Message

    from bot import MP2IBot


class Fun(Cog):
    def __init__(self, bot: MP2IBot) -> None:
        self.kevin_webhook: None | discord.Webhook = None
        self.bot = bot

        # reactions that can be randomly added under these users messages.
        self.users_reactions = {
            726867561924263946: ["🕳️"],
            1015216092920168478: ["🏳‍🌈"],
            433713351592247299: ["🩴"],
            199545535017779200: ["🪜"],
            823477539167141930: ["🥇"],
            533272313588613132: ["🥕"],
            777852203414454273: ["🐀"],
            293463332781031434: ["📉"],
            547496339366215686: ["🥩"],
        }

        # words that trigger the bot to react with a random emoji from the list assigned to the user.
        self.users_triggers: dict[int, list[str]] = {
            726867561924263946: ["bouteille", "boire," "bière", "alcool", "alcoolique", "alcoolisme", "alcoolique"],
            1015216092920168478: ["couleur", "couleurs"],
            433713351592247299: ["tong", "tongs", "gitan"],
            199545535017779200: ["escabeau", "petit"],
            823477539167141930: [
                "champion",
                "championne",
                "championnat",
                "championnats",
                "médaille",
                "médaille",
                "majorant",
            ],
            533272313588613132: ["carotte", "carottes"],
            777852203414454273: ["rat", "rats", "argent", "gratuit", "sous", "paypal"],
            547496339366215686: ["viande", "manger", "broche", "poulet", "sanglier", "steak", "faim"],
        }

    async def cog_load(self) -> None:
        self.general_channel = cast(TextChannel, await self.bot.fetch_channel(MAIN_CHANNEL_ID))
        self.birthday.start()
        self.kevin_say_goodnight.start()

        async def task() -> None:
            await self.bot.wait_until_ready()
            await self.birthday()

        asyncio.create_task(task())

    async def cog_unload(self) -> None:
        self.birthday.stop()

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != GUILD_ID:  # only works into the MP2I guild.
            return
        if message.author.id == message.guild.me.id:
            return

        # the bot is assumed admin on MP2I guild. We will not check permissions.

        if self.is_birthday(message.author.id):  # add 🎉 reaction if birthday
            await message.add_reaction("🎉")

        if "cqfd" in message.content.lower():  # add reaction if "cqfd" in message
            await message.add_reaction("<:prof:1015373456159805440>")

        # add reactions "OUI" on provocation
        if "tu veux te battre" in message.content.lower() or "vous voulez vous battre" in message.content.lower():
            await message.add_reaction("⭕")
            await message.add_reaction("🇺")
            await message.add_reaction("🇮")

        # add special reactions for specific users
        reactions = self.users_reactions.get(message.author.id)
        if reactions:
            # users are able to have multiple reactions assigned, so we select one ! (Not atm)
            reaction = random.choice(reactions)  # nosec

            # only add reactions with a chance of 1/25
            # react randomly or if message contains a trigger word
            triggers = self.users_triggers[message.author.id]
            if random.randint(0, 25) == 0 or any(e in message.content.lower() for e in triggers):
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
    async def prochains_anniv(self, inter: Interaction) -> None:
        if not isinstance(inter.channel, discord.abc.Messageable):
            return

        if not inter.guild or inter.guild.id != GUILD_ID:
            return

        rows: list[str] = []
        now = dt.datetime.now()

        def sorted_key(date: dt.datetime) -> tuple[bool, dt.datetime]:
            passed = date.replace(year=now.year).timestamp() - now.timestamp() < 0
            if passed:  # anniversaire passé
                relative = date.replace(year=now.year + 1)
            else:
                relative = date.replace(year=now.year)

            return passed, relative

        for pi in sorted(self.bot.personal_informations, key=lambda pi: sorted_key(pi.birthdate)):
            ts: int = int(pi.birthdate.timestamp())
            relative = sorted_key(pi.birthdate)[1]

            l = f"{pi.display} ({pi.origin}). <t:{ts}:D> (<t:{int(relative.timestamp())}:R>)"
            if sum(len(row) + 1 for row in rows) > 4000:
                break
            rows.append(l)

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
            "Le ratio est à utiliser avec modération. (Je te le présenterais à l'occasion).", ephemeral=True
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

        guild = self.bot.get_guild(GUILD_ID)
        assert guild is not None

        for pi in self.bot.personal_informations:  # iter over {user_id: birthdate}
            if pi.birthdate.month == now.month and pi.birthdate.day == now.day:
                if pi.discord_id is not None:
                    try:
                        member = guild.get_member(pi.discord_id) or await guild.fetch_member(pi.discord_id)
                    except discord.NotFound:
                        continue

                    current_mp2i_roles = [
                        1146835004144500746,  # MPI
                        1146835141042393100,  # MP2I
                        1146919905296404600,  # PSI
                        1146921479192199299,  # MP
                    ]

                    # Dont spam old students with mentions,
                    # but spam (lovely) current students.
                    if any(role.id in current_mp2i_roles for role in member.roles):
                        send_method = partial(self.general_channel.send, view=TellHappyBirthday(pi.discord_id))
                    else:
                        send_method = self.general_channel.send
                else:
                    send_method = self.general_channel.send

                await send_method(f"Eh ! {pi.display} a anniversaire ! Souhaitez-le lui !")

    @tasks.loop(time=dt.time(hour=22, minute=30, tzinfo=ZoneInfo("Europe/Paris")))
    async def kevin_say_goodnight(self) -> None:
        """
        During our first year, Kevin used to say goodnight to everyone at 10:30pm.
        So now, Kevin-bot will take over this task.
        """
        if random.random() < 0.4:
            return
        if self.kevin_webhook is None:
            wh = await self.general_channel.webhooks()
            if not wh:
                self.kevin_webhook = await self.general_channel.create_webhook(name="Kevin")
            else:
                self.kevin_webhook = wh[0]

        messages = [
            "Allez dormir, les sups !",
            "Le sommeil, c'est pas à négliger ! Au lit !",
            "Bonne nuit, faut aller dormir !",
            "Il est l'heure d'aller se coucher !",
            "Faites de beaux rêves, c'est l'heure de dormir !",
            "Allez, au lit !",
            "Bonne nuit les gens !",
            "Pensez à aller vous coucher !",
        ]

        await self.kevin_webhook.send(
            content=random.choice(messages),
            username="Kevin the bot",
            avatar_url="https://cdn.discordapp.com/avatars/419840551781793802/07d949907dcaaec17429308f3312dd02.webp",
        )


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
    await bot.add_cog(Fun(bot))
