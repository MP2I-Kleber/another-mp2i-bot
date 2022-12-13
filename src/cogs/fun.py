from __future__ import annotations

import datetime as dt
import json
import os
import random
from typing import TYPE_CHECKING, cast

import discord
import openai
import pytz
from discord import AllowedMentions, HTTPException, Member, TextChannel, ui
from discord.app_commands import command, describe, guild_only
from discord.ext import tasks
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]
from discord.utils import find
from typing_extensions import Self

from utils import get_first_and_last_names
from utils.constants import GUILD_ID, OPENIA_CHAT

if TYPE_CHECKING:
    from discord import Interaction, Message

    from bot import MP2IBot


openai.api_key = os.environ.get("OPENIA_API_KEY")


class Fun(Cog):
    def __init__(self, bot: MP2IBot) -> None:
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
        }

        # words that trigger the bot to react with a random emoji from the list assigned to the user.
        self.users_triggers = {
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
        }

        raw_birthdates: dict[str, str]
        if os.path.exists("./data/birthdates.json"):
            with open("./data/birthdates.json", "r") as f:
                raw_birthdates = json.load(f)
        else:
            raw_birthdates = {}

        self.birthdates: dict[int, dt.datetime] = {  # maps from user_ids to datetime
            bot.names_to_ids[get_first_and_last_names(name)]: dt.datetime.strptime(date, r"%d-%m-%Y")
            for name, date in raw_birthdates.items()
        }

    async def cog_load(self) -> None:
        self.general_channel = cast(TextChannel, await self.bot.fetch_channel(1015172827650998352))
        self.birthday.start()

    async def cog_unload(self) -> None:
        self.birthday.stop()

    async def ask_to_openIA(self, message: Message) -> None:
        """Chat with openIA davinci model in discord. No context, no memory, only one message conversation.

        Args:
            message (Message): the message object
        """
        prompt: str = message.content
        response: Any = openai.Completion.create(  # type: ignore
            prompt=prompt,
            engine="text-davinci-003",
            temperature=0.9,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6,
            best_of=1,
            max_tokens=150,
        )
        answer: str = cast(str, response.choices[0].text.strip())  # type: ignore
        await message.channel.send(answer, reference=message)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != GUILD_ID:  # only works into the MP2I guild.
            return
        if message.author.id == message.guild.me.id:
            return

        if openai.api_key is not None and message.channel.id == OPENIA_CHAT:
            await self.ask_to_openIA(message)

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
            if random.randint(0, 25) == 0 or find(
                lambda e: e in message.content.lower(), self.users_triggers[message.author.id]
            ):  # react randomly or if message contains a trigger word # nosec
                await message.add_reaction(reaction)

    def is_birthday(self, user_id: int) -> bool:
        """Tell if a user has birthday or not.

        Args:
            user_id (int): the user to check

        Returns:
            bool: also return False if the birthdate is unknown.
        """
        birthdate = self.birthdates.get(user_id)
        if not birthdate:  # if we don't have any informations about the user birthday, return False.
            return False
        now = dt.datetime.now()
        return birthdate.day == now.day and birthdate.month == now.month

    @command()
    @guild_only()
    async def prochains_anniv(self, inter: Interaction) -> None:
        if not isinstance(inter.channel, discord.abc.Messageable):
            return

        if not inter.guild or inter.guild.id != GUILD_ID:
            return

        lst = ""
        now = dt.datetime.now()

        def sorted_key(date: dt.datetime) -> tuple[bool, dt.datetime]:
            passed = date.replace(year=now.year).timestamp() - now.timestamp() < 0
            if passed:  # anniversaire passé
                relative = date.replace(year=now.year + 1)
            else:
                relative = date.replace(year=now.year)

            return passed, relative

        for user_id, birthday in sorted(self.birthdates.items(), key=lambda t: sorted_key(t[1])):
            ts: int = int(birthday.timestamp())
            name = self.bot.ids_to_names[user_id]

            relative = sorted_key(birthday)[1]

            l = f"{name.first} {name.last[0]}. <t:{ts}:D> (<t:{int(relative.timestamp())}:R>)\n"
            if len(lst + l) > 4000:
                break
            lst += l

        embed = discord.Embed(title="Listes des prochains anniversaires", description=lst)
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

    @tasks.loop(time=dt.time(hour=7, tzinfo=pytz.timezone("Europe/Paris")))
    async def birthday(self) -> None:
        """At 7am, check if it's someone's birthday and send a message if it is."""
        now = dt.datetime.now()
        for user_id, birthday in self.birthdates.items():  # iter over {user_id: birthdate}
            if birthday.month == now.month and birthday.day == now.day:
                # All ids from birthdates needs to be in ids_to_names. Bugs will happen otherwise.
                name = self.bot.ids_to_names[user_id]
                await self.general_channel.send(
                    f"Eh ! {name.first} {name.last[0]}. a anniversaire ! Souhaitez-le lui !",
                    view=TellHappyBirthday(user_id),  # add a button to spam (lovely) the user with mentions.
                )


class TellHappyBirthday(ui.View):
    """A view with a single button to tell a user happy birthday (with mention <3).


    Args:
        user_id (int): the user who had birthday !
    """

    def __init__(self, user_id: int) -> None:

        self.user_id = user_id
        super().__init__(timeout=None)

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
