"""
You can communicate with ChatGPT by mentioning the bot. (Except if the API key is invalid 😧)
"""

from __future__ import annotations

import os
import re
from collections.abc import MutableSequence
from contextlib import nullcontext
from functools import partial
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from core.constants import GUILD_ID
from core.errors import BaseError

if TYPE_CHECKING:
    from discord import Message

    from bot import FISABot


class MessagesCache(MutableSequence[discord.Message]):
    def __init__(self, max_size: int = 100):
        self._internal: list[Message] = []
        self._max_size = max_size
        super().__init__()

    def __getitem__(self, i: int):  # type: ignore[override]
        return self._internal.__getitem__(i)

    def __setitem__(self, i: int, o: Message):  # type: ignore[override]
        return self._internal.__setitem__(i, o)

    def __delitem__(self, i: int):  # type: ignore[override]
        return self._internal.__delitem__(i)

    def __len__(self):
        return self._internal.__len__()

    def insert(self, index: int, value: Message):
        if len(self) >= self._max_size:
            self._internal.pop(0)
        return self._internal.insert(index, value)


class ChatBot(Cog):
    gpt_history_max_size = 10

    def __init__(self, bot: FISABot) -> None:
        self.bot = bot
        self.messages_cache: MessagesCache = MessagesCache()

    async def cog_load(self) -> None:
        try:
            self.openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        except KeyError:
            raise Exception("OPENAI_API_KEY is not set in the environment variables. The extension cannot be loaded.")  # noqa: TRY002

    async def send_chat_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        channel: discord.abc.MessageableChannel | None = None,
        temperature: float = 0.7,
        top_p: float = 1,
        stop: str | list[str] | None = None,
        max_tokens: int | None = 250,
        presence_penalty: float = 0,
        frequency_penalty: float = 0,
        user: str | None = None,
    ):
        create = partial(
            self.openai_client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            n=1,
            stop=stop,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )

        if max_tokens is not None:
            create = partial(create, max_tokens=max_tokens)
        if user is not None:
            create = partial(create, user=user)

        async with channel.typing() if channel else nullcontext():  # interesting syntax! :)
            response = await create()

        answer: str | None = response.choices[0].message.content
        if answer is None:
            raise BaseError("OpenAI responded with None.")
        return answer

    def clean_content(self, content: str) -> str:
        # TODO : replace mentions with usernames ?
        regex = re.compile(r"<@!?1015367382727933963> ?")
        return regex.sub("", content, 0)

    async def get_history(self, message: Message) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = []

        async def inner(msg: Message):
            if len(messages) >= self.gpt_history_max_size:
                return

            if msg not in self.messages_cache:
                self.messages_cache.append(msg)

            me = self.bot.user.id  # type: ignore
            content = self.clean_content(msg.content or "")
            chat: ChatCompletionMessageParam
            if message.author.id == me:
                chat = {"role": "assistant", "content": content}
            else:
                chat = {"role": "user", "content": content}
            messages.insert(0, chat)

            if msg.reference is None:
                return

            match resolved := msg.reference.resolved:
                case None:
                    if msg.reference.message_id is None:
                        return

                    cached = next(
                        (m for m in self.messages_cache if m.id == msg.reference.message_id),
                        None,
                    )
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

    async def ask_to_openai(self, message: Message) -> None:
        """
        Args:
            message (Message): the message object
        """

        messages: list[ChatCompletionMessageParam] = []
        # if random.randint(0, 42) == 0:
        #     messages.append({"role": "system", "content": CHATGPT_SECRET_PROMPT})

        if pi := self.bot.get_personal_information(message.author.id):
            username = pi.firstname
        else:
            username = message.author.display_name

        messages.append({"role": "system", "content": f"The user is called {username}."})

        messages.extend(await self.get_history(message))

        response = await self.send_chat_completion(messages, message.channel, user=username)
        await message.reply(response)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if (
            message.guild is not None
            and message.guild.id == GUILD_ID
            and message.author.id != message.guild.me.id
            and (
                message.guild.me in message.mentions
                or message.reference is not None
                and isinstance(message.reference.resolved, discord.Message)
                and message.reference.resolved.author.id == message.guild.me.id
            )
        ):
            await self.ask_to_openai(message)


async def setup(bot: FISABot) -> None:
    await bot.add_cog(ChatBot(bot))
