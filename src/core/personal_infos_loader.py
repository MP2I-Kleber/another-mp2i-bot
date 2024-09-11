"""
Load personal infos from a file. Personal infos are birthdates, discord ID, etc.
"""

import csv
import logging
import os
from datetime import datetime
from glob import glob
from typing import cast
from zoneinfo import ZoneInfo

from .utils import BraceMessage as __, capitalize

logger = logging.getLogger(__name__)


class PersonalInformation:
    def __init__(
        self,
        firstname: str,
        lastname: str,
        nickname: str,
        discord_id: str,
        birthdate: str,
        origin: str,
    ) -> None:
        if not any((firstname, lastname, nickname)):
            raise ValueError("At least one of firstname, lastname or nickname must be set.")  # noqa: TRY003
        self.firstname: str | None = capitalize(firstname) if firstname else None
        self.lastname: str | None = lastname.upper() if lastname else None
        self.nickname: str | None = nickname or None
        self.origin = origin

        if discord_id:
            self.discord_id = int(discord_id)
        else:
            self.discord_id = None

        self.birthdate = datetime.strptime(birthdate, r"%d/%m/%Y").astimezone(tz=ZoneInfo("Europe/Paris"))

    @property
    def display(self):
        if self.nickname:
            return self.nickname

        parts = [cast(str, self.firstname)]
        if self.lastname:
            parts.append(f"{self.lastname[0]}.")
        return " ".join(parts)


def load_personal_informations() -> list[PersonalInformation]:
    result: list[PersonalInformation] = []

    def read(filename: str):
        origin = os.path.splitext(os.path.basename(filename))[0]
        with open(csv_file, encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f)):
                try:
                    yield PersonalInformation(**row, origin=origin)
                except ValueError as e:
                    logger.warning(__("Row {} is invalid in {}.csv: {}", i + 1, origin, e))

    for csv_file in glob("./resources/personal_informations/*.csv"):
        if csv_file == "./resources/personal_informations/example.csv":
            continue
        logger.debug(__("Reading {}", csv_file))
        result.extend(read(csv_file))

    return result
