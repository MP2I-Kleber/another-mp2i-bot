# inspired by https://github.com/Rapptz/discord.py/blob/master/discord/client.py

import asyncio
import logging
import os
import sys
import traceback
from collections.abc import Coroutine
from typing import Any, ClassVar, NamedTuple, cast

import aiohttp
import discord

dt_fmt = "%Y-%m-%d %H:%M:%S"


def stream_supports_color(stream: Any) -> bool:
    is_a_tty = hasattr(stream, "isatty") and stream.isatty()

    if sys.platform != "win32":
        return is_a_tty

    # ANSICON checks for things like ConEmu
    # WT_SESSION checks if this is Windows Terminal
    # VSCode built-in terminal supports colour too
    return is_a_tty and (
        "ANSICON" in os.environ or "WT_SESSION" in os.environ or os.environ.get("TERM_PROGRAM") == "vscode"
    )


class AdditionalContext(NamedTuple):
    guild: discord.Guild | None
    user: discord.User | discord.Member


class DiscordLogHandler(logging.Handler):
    bind_colors: ClassVar = {
        logging.WARNING: discord.Color.yellow(),
        logging.INFO: discord.Color.blue(),
        logging.ERROR: discord.Color.red(),
        logging.CRITICAL: discord.Color.red(),
        logging.DEBUG: discord.Color.orange(),
    }

    tasks: ClassVar[list[asyncio.Task[Any]]] = []
    delayed_logs: ClassVar[list[list[discord.Embed]]] = []
    webhook_url: ClassVar[str | None] = os.environ.get("LOGGER_WEBHOOK")

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)

    @property
    def event_loop(self) -> asyncio.AbstractEventLoop | None:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    def send_to_discord(self, record: logging.LogRecord):
        embed = discord.Embed()
        embeds = [embed]
        embed.set_author(name=f"{record.levelname} : {record.name}")
        embed.description = f"File : `{record.pathname}`\nLine : `{record.lineno}`\nMessage : `{record.message}`"

        if record.exc_info:
            formatted_tb = traceback.format_exception(record.exc_info[1])
            string_tb = "".join(formatted_tb)
            if len(string_tb) > 4000:
                string_tb = f"{string_tb[:2000]} \n\n ... \n\n {string_tb[-2000:]}"
            tb_embed = discord.Embed()

            tb_embed.description = f"```py\n{string_tb}```"
            embeds.append(tb_embed)

        additional_context = getattr(record, "additional_context", None)
        if additional_context is not None:
            additional_context = cast(AdditionalContext, additional_context)

            def format_guild(guild: discord.Guild | None) -> str:
                if guild is None:
                    return "Private Message"
                return f"`{guild.name}` ({guild.id})"

            embed.add_field(
                name="Additional Context",
                value=(
                    f"User : `{additional_context.user.name}#{additional_context.user.discriminator}`"
                    f" ({additional_context.user.id})\n"
                    f"Guild : {format_guild(additional_context.guild)}\n"
                ),
            )

        for embed in embeds:
            embed.color = self.bind_colors.get(record.levelno, None)

        if self.event_loop:
            self.create_task(self.send_webhook(embeds))
        else:
            self.delayed_logs.append(embeds)

    def create_task(self, coro: Coroutine[Any, Any, Any]):
        event_loop = cast(asyncio.AbstractEventLoop, self.event_loop)
        task = event_loop.create_task(coro)
        task.add_done_callback(self.purge_task)
        self.tasks.append(task)

    async def send_webhook(self, embeds: list[discord.Embed]):
        url = cast(str, self.webhook_url)
        async with aiohttp.ClientSession() as session:
            wh = discord.Webhook.from_url(url, session=session)
            await wh.send(embeds=embeds)

    async def send_delayed_logs(self):
        acc: list[discord.Embed] = []
        for embeds in self.delayed_logs:
            if len(acc) + len(embeds) <= 10:
                acc.extend(embeds)
            else:
                await self.send_webhook(acc)
                acc = embeds.copy()
        DiscordLogHandler.delayed_logs = []
        if acc:
            await self.send_webhook(acc)

    def purge_task(self, task: asyncio.Task[Any]):
        self.tasks.remove(task)

    def emit(self, record: logging.LogRecord):
        # Send the delayed logs as soon as possible
        # This isn't perfect. The log will only be transmitted when a WARNING message will be sent.
        # But the bot log a warning message when it is ready, to "fix" this problem.
        if self.event_loop and self.delayed_logs:
            self.create_task(self.send_delayed_logs())

        if getattr(record, "ignore_discord", False):
            return

        if self.webhook_url is None:
            return

        self.send_to_discord(record)


class _ColorFormatter(logging.Formatter):
    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS: ClassVar = [
        (logging.DEBUG, "\x1b[40;1m"),
        (logging.INFO, "\x1b[34;1m"),
        (logging.WARNING, "\x1b[33;1m"),
        (logging.ERROR, "\x1b[31m"),
        (logging.CRITICAL, "\x1b[41m"),
    ]

    FORMATS: ClassVar = {
        level: logging.Formatter(
            f"\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m %(message)s",
            dt_fmt,
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record: logging.LogRecord) -> str:
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f"\x1b[31m{text}\x1b[0m"

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


def create_logger(name: str | None = None, log_file: str | None = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    stream_handler = logging.StreamHandler()
    if stream_supports_color(stream_handler.stream):
        stream_handler.setFormatter(_ColorFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
        )
    logger.addHandler(stream_handler)

    discord_log_handler = DiscordLogHandler()
    discord_log_handler.setFormatter(logging.Formatter())
    logger.addHandler(discord_log_handler)

    if log_file is not None:
        log_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)

    return logger
