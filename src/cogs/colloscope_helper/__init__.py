from __future__ import annotations

import io
import logging
import os
from glob import glob
from typing import TYPE_CHECKING, Literal, cast

import discord
from discord import app_commands
from discord.ext import commands
from pdf2image.pdf2image import convert_from_bytes

from core.utils import BraceMessage as __

from . import colloscope_maker as cm

if TYPE_CHECKING:
    from bot import MP2IBot


logger = logging.getLogger(__name__)


class PlanningHelper(
    commands.GroupCog, group_name="colloscope", group_description="Un utilitaire pour gérer le colloscope"
):
    def __init__(self, bot: MP2IBot):
        self.bot = bot

        self.colloscopes: dict[str, cm.Colloscope] = {}

        for csv_file in glob("./resources/personal_informations/*.csv"):
            class_ = os.path.splitext(os.path.basename(csv_file))[0]
            try:
                self.colloscopes[class_] = cm.load_colloscope(csv_file)
            except Exception:
                logger.warning(
                    __("Error while reading the colloscope from : {filename}", filename=csv_file), stack_info=True
                )

        decorator = app_commands.choices(class_=[app_commands.Choice(name=k, value=k) for k in self.colloscopes])
        decorator(self.quicklook)
        decorator(self.export)
        decorator(self.next_colle)

    @app_commands.command(name="aperçu", description="Affiche l'aperçu du colloscope")
    @app_commands.rename(class_="classe", group="groupe")
    @app_commands.describe(class_="Votre classe.", group="Votre groupe de colle.")
    async def quicklook(self, inter: discord.Interaction, class_: str, group: int):
        colloscope = self.colloscopes[class_]
        colles = cm.sort_colles(colloscope.colles, sort_type="temps")  # sort by time

        filtered_colles = [c for c in colles if c.group == str(group)]
        if not filtered_colles:
            raise ValueError("Aucune colle n'a été trouvé pour ce groupe")

        buffer = io.BytesIO()
        cm.write_colles(buffer, "pdf", filtered_colles, str(group), colloscope.holidays)
        buffer.seek(0)
        images = convert_from_bytes(buffer.read())

        files: list[discord.File] = []
        for i, img in enumerate(images):
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="png")
            img_buffer.seek(0)
            files.append(discord.File(img_buffer, f"{i}.png"))

        await inter.response.send_message(files=files)

    @app_commands.command(name="export", description="Exporte le colloscope dans un fichier")
    @app_commands.rename(class_="classe", group="groupe")
    @app_commands.describe(
        class_="Votre classe", group="Votre groupe de colle", format="Le format du fichier à exporter"
    )
    async def export(
        self,
        inter: discord.Interaction,
        class_: str,
        group: int,
        format: Literal["pdf", "csv", "agenda", "todoist"] = "pdf",
    ):
        colloscope = self.colloscopes[class_]

        colles = cm.sort_colles(colloscope.colles, sort_type="temps")  # sort by time
        filtered_colles = [c for c in colles if c.group == str(group)]
        if not filtered_colles:
            raise ValueError("Aucune colle n'a été trouvé pour ce groupe")

        if format in ["agenda", "csv", "todoist"]:
            format = cast(Literal["agenda", "csv", "todoist"], format)
            buffer = io.StringIO()
            cm.write_colles(buffer, format, filtered_colles, str(group), colloscope.holidays)
            buffer = io.BytesIO(buffer.getvalue().encode())
        else:
            format = cast(Literal["pdf"], format)
            buffer = io.BytesIO()
            cm.write_colles(buffer, format, filtered_colles, str(group), colloscope.holidays)
        buffer.seek(0)
        file = discord.File(buffer, filename=f"colloscope.{format}")
        await inter.response.send_message(file=file)

    @app_commands.command(name="prochaine_colle", description="Affiche la prochaine colle")
    @app_commands.rename(class_="classe", group="groupe", nb="nombre")
    @app_commands.describe(class_="Votre classe.", group="Votre groupe de colle.", nb="Le nombre de colle à afficher.")
    async def next_colle(self, inter: discord.Interaction, class_: str, group: int, nb: int = 5):
        colloscope = self.colloscopes[class_]

        sorted_colles = cm.get_group_upcoming_colles(colloscope.colles, str(group))
        output_text = f"### __Liste des {min(nb, len(sorted_colles), 12 )} prochaines Colles du groupe {group} :__\n"

        for i in range(min(nb, len(sorted_colles), 12)):
            date = sorted_colles[i].long_str_date
            output_text += f"**{date.title()} : {sorted_colles[i].hour}** - __{sorted_colles[i].subject}__ - en {sorted_colles[i].classroom} avec {sorted_colles[i].professor}\n"
        await inter.response.send_message(output_text)


async def setup(bot: MP2IBot):
    await bot.add_cog(PlanningHelper(bot))
