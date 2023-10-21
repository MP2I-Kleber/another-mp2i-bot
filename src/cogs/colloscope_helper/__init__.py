import os
from typing import TYPE_CHECKING, Literal

import discord
from discord import app_commands
from discord.ext import commands
from pdf2image.pdf2image import convert_from_path  # type: ignore

from . import colloscope_maker as cm

if TYPE_CHECKING:
    from bot import MP2IBot


class PlanningHelper(
    commands.GroupCog, group_name="colloscope", group_description="Un utilitaire pour gérer le colloscope"
):
    def __init__(self, bot: MP2IBot):
        self.bot = bot

    @app_commands.command(name="aperçu", description="Affiche l'aperçu du colloscope")
    @app_commands.rename(group="groupe")
    @app_commands.describe(group="Votre groupe de colle")
    async def quicklook(self, inter: discord.Interaction, group: int):
        file = cm.main(str(group), "pdf")
        images = convert_from_path(file)  # type: ignore

        for i in range(len(images)):  # on envoie une image pdf de tout le colloscope du groupe
            images[i].save(os.path.join("./temp/", "page" + str(i) + ".jpg"), "JPEG")
            await inter.response.send_message(file=discord.File(os.path.join("./temp/", "page" + str(i) + ".jpg")))

        for i in range(len(images)):  # on supprime le fichier temporaire crée
            os.remove(os.path.join("./temp/", "page" + str(i) + ".jpg"))

    @app_commands.command(name="export", description="Exporte le colloscope dans un fichier")
    @app_commands.rename(group="groupe")
    @app_commands.describe(group="Votre groupe de colle", format="Le format du fichier à exporter")
    async def export(self, inter: discord.Interaction, group: int, format: Literal["pdf", "csv", "agenda"] = "pdf"):
        file = cm.main(str(group), format)

        if file == "Aucune colle n'a été trouvé pour ce groupe" or not file:  # teste si aucune colle n'a été trouvé
            await inter.response.send_message("Aucune colle n'a été trouvé pour ce groupe")
            return

        with open(file, "rb") as f:  # si une colle à été trouvé, on l'envoie à l'utilisateur
            pdf = discord.File(f, filename=os.path.basename(file))

        await inter.response.send_message(file=pdf)

    @app_commands.command(name="prochaine_colle", description="Affiche la prochaine colle")
    @app_commands.rename(group="groupe", nb="nombre")
    @app_commands.describe(group="Votre groupe de colle", nb="Le nombre de colle à afficher")
    async def next_colle(self, inter: discord.Interaction, group: int, nb: int = 5):
        sorted_colles = cm.get_group_upcoming_colles(str(group))  # reçois le colloscope trié
        outputText = f"### __Liste des {min(nb, len(sorted_colles), 12 )} prochaines Colles du groupe {group} :__\n"

        for i in range(min(nb, len(sorted_colles), 12)):  # affiche le bon nombre de fois les colles
            date = sorted_colles[i].long_str_date
            outputText += f"**{date.title()} : {sorted_colles[i].hour}** - __{sorted_colles[i].subject}__ - en {sorted_colles[i].classroom} avec {sorted_colles[i].professor}\n"
        await inter.response.send_message(outputText)


async def setup(bot: MP2IBot):
    await bot.add_cog(PlanningHelper(bot))
