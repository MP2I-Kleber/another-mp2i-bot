from __future__ import annotations

import enum
from operator import attrgetter

import httpx

from .models import MachineInformations, MachineState as MachineState

BASE_URL = "https://api.touchnpay.fr/public/"


class BATIMENT(enum.Enum):
    U5 = "30dwf80glk9ezrig"
    U7 = "30dwf80glk9ezzr9"


async def get_machine_state(bat: BATIMENT) -> list[MachineInformations]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{bat.value}")
    return sorted([MachineInformations.model_validate(info) for info in response.json()], key=attrgetter("machine_nbr"))


if __name__ == "__main__":
    import asyncio

    async def main():
        print(await get_machine_state(BATIMENT.U5))

    asyncio.run(main())
