from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal, NamedTuple

import discord

# import humanize
from discord import app_commands
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]
from discord.utils import get

from utils import ResponseType, response_constructor
from utils.constants import GUILD_ID
from utils.cts_api import get_lines, get_stop_times, get_stops
from utils.errors import BaseError

if TYPE_CHECKING:
    from discord import Embed, Emoji, Interaction

    from bot import MP2IBot


logger = logging.getLogger(__name__)


@dataclass
class Stop:
    name: str
    ref: str

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Stop) and self.name == other.name and self.ref == other.ref


class StopTime(NamedTuple):
    type: Literal["bus", "tram"]
    destination: str
    line: str
    arrival: datetime


class CTS(Cog):
    def __init__(self, bot: MP2IBot):
        self.bot = bot
        self.emojis: dict[str, Emoji] = {}

    async def cog_load(self) -> None:
        stops = await get_stops()
        stops_list = stops["StopPointsDelivery"]["AnnotatedStopPointRef"]
        if stops_list is None:
            logger.warning("Could not find any stop stations ?")
            raise Exception("Could not find any stop stations ?")

        self.stops: list[Stop] = []
        for stop_paylod in stops_list:
            if stop_paylod["StopName"] is None or stop_paylod["Extension"]["LogicalStopCode"] is None:
                continue

            stop = Stop(name=stop_paylod["StopName"], ref=stop_paylod["Extension"]["LogicalStopCode"])
            if stop in self.stops:
                continue
            self.stops.append(stop)

        lines = await get_lines()
        lines_list = lines["LinesDelivery"]["AnnotatedLineRef"]
        if lines_list is None:
            logger.warning("Could not get any lines ?")
            lines_names: list[str] = []
        else:
            lines_names: list[str] = [line["LineRef"] for line in lines_list if line["LineRef"] is not None]

        guild = await self.bot.fetch_guild(GUILD_ID)
        for line_name in lines_names:
            if line_name in self.emojis:
                continue
            emoji = get(guild.emojis, name="_" + line_name)
            if not emoji:
                continue
            self.emojis[line_name] = emoji

    @app_commands.command()
    @app_commands.guilds(GUILD_ID)
    @app_commands.rename(stop_ref="arrêt")
    async def cts_next(self, inter: Interaction, stop_ref: str):
        await inter.response.defer()
        stop = get(self.stops, ref=stop_ref)
        if not stop:
            raise BaseError("Arrêt non trouvé !")

        tmp = await get_stop_times(stop.ref)
        tmp = tmp["ServiceDelivery"]["StopMonitoringDelivery"]

        if tmp is None or not tmp:
            raise BaseError("Quelque chose de plutôt inattendu s'est passé !")

        times: list[StopTime] = []
        for tmp in tmp[0]["MonitoredStopVisit"]:
            vehicle = tmp["MonitoredVehicleJourney"]

            if vehicle["VehicleMode"] not in ("bus", "tram"):
                continue

            times.append(
                StopTime(
                    type=vehicle["VehicleMode"],
                    destination=vehicle["DestinationName"] or "??",
                    line=vehicle["LineRef"] or "??",
                    arrival=datetime.fromisoformat(vehicle["MonitoredCall"]["ExpectedArrivalTime"]),
                )
            )

        embed = response_constructor(ResponseType.info, f"Prochaines arrivées pour {stop.name}")["embed"]

        embeds_data: dict[str, str] = {}
        groups: dict[tuple[str, str, str], list[int]] = {}

        for time in sorted(times, key=lambda t: t.arrival):
            groups.setdefault((time.type, time.line, time.destination), [])

            ts: int = int(time.arrival.timestamp())
            groups[(time.type, time.line, time.destination)].append(ts)

        for group, group_times in groups.items():
            key = group[0].capitalize()
            embeds_data.setdefault(key, "")
            embeds_data[key] += (
                f"**{self.emojis.get(group[1], group[1])} ➜ {group[2]}**\n"
                + ", ".join(f"<t:{ts}:R>" for ts in group_times)
                + "\n"
            )

        embeds: list[Embed] = [embed]
        for name, value in embeds_data.items():
            embeds.append(discord.Embed(title=name, description=value, color=embeds[0].color))

        await inter.edit_original_response(embeds=embeds)

    @cts_next.autocomplete("stop_ref")
    async def extension_autocompleter(self, inter: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=stop.name, value=stop.ref)
            for stop in self.stops
            if stop.name.lower().startswith(current.lower()) or current.lower() in stop.name.lower()
        ][:25]


async def setup(bot: MP2IBot):
    await bot.add_cog(CTS(bot))
