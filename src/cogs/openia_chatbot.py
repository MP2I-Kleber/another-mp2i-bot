"""
You can communicate with ChatGPT by mentioning the bot. (Except if the API key is invalid 😧)
"""

from __future__ import annotations

import os
import random
import re
from collections.abc import MutableSequence
from contextlib import nullcontext
from typing import TYPE_CHECKING, cast

import discord
import openai
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]

from core.constants import CHATGPT_SECRET_PROMPT, GUILD_ID

if TYPE_CHECKING:
    from discord import Message

    from bot import MP2IBot


class MessagesCache(MutableSequence[discord.Message]):
    def __init__(self, max_size: int = 100):
        self._internal: list[Message] = list()
        self._max_size = max_size
        super().__init__()

    def __getitem__(self, i: int):  # type: ignore (no range select)
        return self._internal.__getitem__(i)

    def __setitem__(self, i: int, o: Message):
        return self._internal.__setitem__(i, o)

    def __delitem__(self, i: int):
        return self._internal.__delitem__(i)

    def __len__(self):
        return self._internal.__len__()

    def insert(self, index: int, value: Message):
        if len(self) >= self._max_size:
            self._internal.pop(0)
        return self._internal.insert(index, value)


class ChatBot(Cog):
    gpt_history_max_size = 10

    def __init__(self, bot: MP2IBot) -> None:
        self.bot = bot
        self.messages_cache: MessagesCache = MessagesCache()

    async def cog_load(self) -> None:
        try:
            openai.api_key = os.environ["OPENIA_API_KEY"]
        except KeyError:
            raise Exception("OPENIA_API_KEY is not set in the environment variables. The extension cannot be loaded.")

    async def send_chat_completion(
        self,
        messages: list[dict[str, str]],
        channel: discord.abc.MessageableChannel | None = None,
        temperature: float = 0.7,
        top_p: float = 1,
        stop: str | list[str] | None = None,
        max_tokens: int | None = 250,
        presence_penalty: float = 0,
        frequency_penalty: float = 0,
        user: str | None = None,
    ):
        kwargs = {
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "n": 1,
            "stop": stop,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        }

        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if user is not None:
            kwargs["user"] = user

        async with channel.typing() if channel else nullcontext():  # interesting syntax! :)
            response = await openai.ChatCompletion.acreate(**kwargs)  # type: ignore

        answer: str = cast(str, response.choices[0].message.content)  # type: ignore
        return answer

    def clean_content(self, content: str) -> str:
        # TODO : replace mentions with usernames ?
        regex = re.compile(r"<@!?1015367382727933963> ?")
        return regex.sub("", content, 0)

    async def get_history(self, message: Message) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        async def inner(msg: Message):
            if len(messages) >= self.gpt_history_max_size:
                return

            if msg not in self.messages_cache:
                self.messages_cache.append(msg)

            me = self.bot.user.id  # type: ignore
            if message.author.id == me:
                role = "assistant"
            else:
                role = "user"
            messages.insert(0, {"role": role, "content": self.clean_content(msg.content or "")})

            if msg.reference is None:
                return

            match resolved := msg.reference.resolved:
                case None:
                    if msg.reference.message_id is None:
                        return

                    cached = next((m for m in self.messages_cache if m.id == msg.reference.message_id), None)
                    if cached is not None:
                        await inner(cached)
                        return

                    try:
                        msg = await msg.channel.fetch_message(msg.reference.message_id)
                    except (discord.NotFound, discord.HTTPException):
                        pass
                    else:
                        await inner(msg)
                case discord.Message():
                    await inner(resolved)
                case discord.DeletedReferencedMessage():
                    pass

        await inner(message)
        return messages

    async def ask_to_openIA(self, message: Message) -> None:
        """Chat with openIA davinci model in discord. No context, no memory, only one message conversation.

        Args:
            message (Message): the message object
        """

        messages: list[dict[str, str]] = []
        if random.randint(0, 42) == 0:
            messages.append({"role": "system", "content": CHATGPT_SECRET_PROMPT})

        if pi := self.bot.get_personal_information(message.author.id):
            username = pi.firstname
        else:
            username = message.author.display_name

        messages.append({"role": "system", "content": f"The user is called {username}."})

        # remove the mention if starts with @bot blabla
        messages.extend(await self.get_history(message))

        response = await self.send_chat_completion(messages, message.channel, user=username)
        await message.reply(response)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != GUILD_ID:  # only works into the MP2I guild.
            return
        if message.author.id == message.guild.me.id:
            return

        if (
            message.guild.me in message.mentions
            or message.reference is not None
            and isinstance(message.reference.resolved, discord.Message)
            and message.reference.resolved.author.id == message.guild.me.id
        ):
            await self.ask_to_openIA(message)


async def setup(bot: MP2IBot) -> None:
    await bot.add_cog(ChatBot(bot))
