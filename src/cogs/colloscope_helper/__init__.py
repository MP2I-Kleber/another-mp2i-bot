from __future__ import annotations

import io
from typing import TYPE_CHECKING, Literal, cast

import discord
from discord import app_commands
from discord.ext import commands
from pdf2image.pdf2image import convert_from_bytes

from core.constants import COLLOSCOPE_MPI_PATH, COLLOSCOPE_MP2I_PATH

from . import colloscope_maker as cm

if TYPE_CHECKING:
    from bot import MP2IBot

def userClass(user: discord.Member):
    if discord.utils.get(user.roles, name="state.MPI"):
        return "MPI"
    elif discord.utils.get(user.roles, name="state.MP2I"):
        return "MP2I"


class PlanningHelper(
    commands.GroupCog, group_name="colloscope", group_description="Un utilitaire pour gérer le colloscope"
):
    def __init__(self, bot: MP2IBot):
        self.bot = bot
        self.collesMPI = cm.get_all_colles(str(COLLOSCOPE_MPI_PATH))
        self.holidaysMPI = cm.get_holidays(str(COLLOSCOPE_MPI_PATH))
        self.collesMP2I = cm.get_all_colles(str(COLLOSCOPE_MP2I_PATH))
        self.holidaysMP2I = cm.get_holidays(str(COLLOSCOPE_MP2I_PATH))

    @app_commands.command(name="aperçu", description="Affiche l'aperçu du colloscope")
    @app_commands.rename(group="groupe")
    @app_commands.describe(group="Votre groupe de colle")
    async def quicklook(self, inter: discord.Interaction, group: int):
        user = inter.user

        if userClass(user) == "MPI":
            colles = cm.sort_colles(self.collesMPI, sort_type="temps")
            holidays = self.holidaysMPI
        elif userClass(user) == "MP2I":
            colles = cm.sort_colles(self.collesMP2I, sort_type="temps")
            holidays = self.holidaysMP2I
        else:
            raise ValueError("Vous n'êtes pas dans une classe")

        filtered_colles = [c for c in colles if c.group == str(group)]
        if not filtered_colles:
            raise ValueError("Aucune colle n'a été trouvé pour ce groupe")

        buffer = io.BytesIO()
        cm.write_colles(buffer, "pdf", filtered_colles, str(group), holidays)
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
    @app_commands.rename(group="groupe")
    @app_commands.describe(group="Votre groupe de colle", format="Le format du fichier à exporter")
    async def export(self, inter: discord.Interaction, group: int, format: Literal["pdf", "csv", "agenda", "todoist"] = "pdf"):
        user = inter.user

        if userClass(user) == "MPI":
            colles = cm.sort_colles(self.collesMPI, sort_type="temps")
            holidays = self.holidaysMPI
        elif userClass(user) == "MP2I":
            colles = cm.sort_colles(self.collesMP2I, sort_type="temps")
            holidays = self.holidaysMP2I
        else:
            raise ValueError("Vous n'êtes pas dans une classe")

        filtered_colles = [c for c in colles if c.group == str(group)]
        if not filtered_colles:
            raise ValueError("Aucune colle n'a été trouvé pour ce groupe")

        if format in ["agenda", "csv", "todoist"]:
            format = cast(Literal["csv", "agenda", "todoist"], format)
            buffer = io.StringIO()
            cm.write_colles(buffer, format, filtered_colles, str(group), holidays)
            buffer = io.BytesIO(buffer.getvalue().encode())
            format = "csv"
        else:
            format = cast(Literal["pdf"], format)
            buffer = io.BytesIO()
            cm.write_colles(buffer, format, filtered_colles, str(group), holidays)
        buffer.seek(0)
        file = discord.File(buffer, filename=f"colloscope.{format}")
        await inter.response.send_message(file=file)

    @app_commands.command(name="prochaine_colle", description="Affiche la prochaine colle")
    @app_commands.rename(group="groupe", nb="nombre")
    @app_commands.describe(group="Votre groupe de colle", nb="Le nombre de colle à afficher")
    async def next_colle(self, inter: discord.Interaction, group: int, nb: int = 5):
        user = inter.user

        if userClass(user) == "MPI":
            colles = cm.sort_colles(self.collesMPI, sort_type="temps")
        elif userClass(user) == "MP2I":
            colles = cm.sort_colles(self.collesMP2I, sort_type="temps")
        else:
            raise ValueError("Vous n'êtes pas dans une classe")

        sorted_colles = cm.get_group_upcoming_colles(colles, str(group))
        output_text = f"### __Liste des {min(nb, len(sorted_colles), 12 )} prochaines Colles du groupe {group} :__\n"

        for i in range(min(nb, len(sorted_colles), 12)):
            date = sorted_colles[i].long_str_date
            output_text += f"**{date.title()} : {sorted_colles[i].hour}** - __{sorted_colles[i].subject}__ - en {sorted_colles[i].classroom} avec {sorted_colles[i].professor}\n"
        await inter.response.send_message(output_text)


async def setup(bot: MP2IBot):
    await bot.add_cog(PlanningHelper(bot))
