from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, cast

import discord
import httpx
from discord.ext import commands, tasks

from libraries.washingmachines import BATIMENT, MachineState, get_machine_state

if TYPE_CHECKING:
    from bot import FISABot
    from libraries.washingmachines.models import MachineInformations

    InfosT = dict[BATIMENT, list[MachineInformations]]

logger = logging.getLogger(__name__)


class WashingMachines(commands.Cog):
    state_message: discord.Message

    def __init__(self, bot: FISABot):
        self.bot = bot
        self.setup_task = None

    async def cog_load(self):
        def cleanup(_: asyncio.Task[Any]):
            self.setup_task = None

        self.setup_task = asyncio.create_task(self.cog_load_ready())
        self.setup_task.add_done_callback(cleanup)

    async def cog_load_ready(self):
        await self.bot.wait_until_ready()

        infos = await self.get_infos()
        embeds = self.build_embeds(infos)
        msg = await self.get_state_message()
        if msg is None:
            channel = cast(discord.TextChannel, self.bot.get_channel(self.bot.config.washing_machine_state_channel))
            msg = await channel.send(embeds=embeds)
        else:
            await msg.edit(embeds=embeds)

        self.state_message = msg
        self.maintain_state.start()

    async def cog_unload(self):
        self.maintain_state.cancel()

    @tasks.loop(minutes=1)
    async def maintain_state(self):
        try:
            infos = await self.get_infos()
        except httpx.HTTPError:
            logger.exception("An error occurred while getting washing machines informations.")
            return
        except json.decoder.JSONDecodeError:
            logger.exception("An error occurred while parsing the json informations")
            return
        except Exception:
            logger.exception("An unknown error occurred.")
            return

        embeds = self.build_embeds(infos)
        await self.state_message.edit(embeds=embeds)

    async def get_state_message(self) -> discord.Message | None:
        channel = cast(discord.TextChannel, self.bot.get_channel(self.bot.config.washing_machine_state_channel))
        bot_user = cast(discord.ClientUser, self.bot.user)

        async for msg in channel.history():
            if msg.author.id == bot_user.id:
                return msg

    async def get_infos(self) -> InfosT:
        return {bat: await get_machine_state(bat) for bat in BATIMENT}

    def build_embeds(self, infos: InfosT):
        embeds = [discord.Embed(title="État des machines", color=0x2B2D31)]

        for batiment, machines in infos.items():
            embed = discord.Embed(
                title=f"Bâtiment {batiment.name}",
                url=f"https://gad.touchnpay.fr/fr/public/material/{batiment.value}",
            )
            if any(machine.machine_state == MachineState.AVAILABLE for machine in machines):
                embed.color = 0x57F287
            else:
                embed.color = 0xED4245

            for machine in machines:
                value_constructor: dict[str, str] = {}

                state = "Occupé" if machine.machine_state == MachineState.IN_SERVICE else "Disponible"
                value_constructor["état"] = state

                if machine.started_at:
                    value_constructor["depuis"] = f"<t:{int(machine.started_at.timestamp())}:R>"

                padding = max(map(len, value_constructor.keys()))
                value = "\n".join(f"`{key: <{padding}} :` {val}" for key, val in value_constructor.items())

                emoji = ":x:" if machine.machine_state == MachineState.IN_SERVICE else ":white_check_mark:"
                embed.add_field(name=f"{emoji} {machine.machine_name}", value=value)

            embeds.append(embed)
        return embeds


async def setup(bot: FISABot):
    await bot.add_cog(WashingMachines(bot))
