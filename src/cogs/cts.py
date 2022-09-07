from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal, NamedTuple

# import humanize
from discord import app_commands
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]
from discord.utils import get

from utils import ResponseType, response_constructor
from utils.constants import GUILD_ID
from utils.cts_api import get_stop_times, get_stops
from utils.errors import BaseError

if TYPE_CHECKING:
    from discord import Interaction

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


class Admin(Cog):
    def __init__(self, bot: MP2IBot):
        self.bot = bot

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

        fields_payload: dict[str, str] = {}

        for time in sorted(times, key=lambda t: t.arrival):
            fields_payload.setdefault(time.type, "")

            ts: int = int(time.arrival.timestamp())
            fields_payload[time.type] += f"**{time.line}** -> {time.destination} : <t:{ts}:R>\n"

        for name, value in fields_payload.items():
            embed.add_field(name=name, value=value, inline=False)

        await inter.edit_original_response(embed=embed)

    @cts_next.autocomplete("stop_ref")
    async def extension_autocompleter(self, inter: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=stop.name, value=stop.ref)
            for stop in self.stops
            if stop.name.lower().startswith(current.lower()) or current.lower() in stop.name.lower()
        ][:25]


async def setup(bot: MP2IBot):
    await bot.add_cog(Admin(bot))
