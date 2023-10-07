from typing import TYPE_CHECKING, Literal

import discord
from discord import app_commands
from discord.ext import commands

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
    async def quicklook(self, inter: discord.Interaction, group: str):
        pass

    @app_commands.command(name="export", description="Exporte le colloscope dans un fichier")
    @app_commands.rename(group="groupe")
    @app_commands.describe(group="Votre groupe de colle", format="Le format du fichier à exporter")
    async def export(self, inter: discord.Interaction, group: str, format: Literal["pdf", "csv", "agenda"] = "pdf"):
        pass

    @app_commands.command(name="prochaine_colle", description="Affiche la prochaine colle")
    @app_commands.rename(group="groupe", nb="nombre")
    @app_commands.describe(group="Votre groupe de colle", nb="Le nombre de colle à afficher")
    async def next_colle(self, inter: discord.Interaction, group: str, nb: int = 1):
        pass
