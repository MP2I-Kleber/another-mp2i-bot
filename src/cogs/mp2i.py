from __future__ import annotations

import json
import random
from io import BytesIO
from typing import TYPE_CHECKING, Any, TypedDict, cast

import discord
from discord import app_commands, ui
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]
from PIL import Image, ImageDraw
from typing_extensions import Self

from core.utils import ResponseType, response_constructor

if TYPE_CHECKING:
    from discord import Interaction

    from bot import MP2IBot


class Level(TypedDict):
    id: int
    rid: int
    ctl: str


space = 20
border_width = 10
center_circle_radius = 45

border_color = (100, 100, 255)

plus_w, plus_h = (60, 60)

plus = Image.open("./resources/images/plus.png").convert("RGBA")
plus = plus.resize((plus_w, plus_h), resample=Image.Resampling.LANCZOS)
plus.paste(border_color, mask=plus)


class MP2IGame(Cog):
    def __init__(self, bot: MP2IBot) -> None:
        self.bot = bot
        self._borders: Image.Image | None = None

        self.levels: list[Level] = self.load_levels()

    @staticmethod
    def load_levels() -> list[Level]:
        with open("./resources/mp2i_game_levels.json", "r") as f:
            return json.load(f)

    @staticmethod
    def load_images_level(level_rid: int) -> tuple[Image.Image, Image.Image]:
        first = Image.open(f"./resources/images/mp2i_game/_{level_rid}_1.jpg")
        second = Image.open(f"./resources/images/mp2i_game/_{level_rid}_2.jpg")

        return (first, second)

    @staticmethod
    def generate_image_assembly(images: tuple[Image.Image, Image.Image]) -> BytesIO:
        image_w, image_h = images[0].size

        result = Image.new(
            "RGBA",
            ((image_w + (space * 3) // 2 + border_width * 2) * 2, (image_h + space * 2 + border_width * 2)),
            color=(150, 100, 100, 0),
        )

        result_w, result_h = result.size

        borders = Image.new("RGBA", (result_w * 4, result_h * 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(borders)
        draw.rectangle(
            (
                (space * 4, space * 4),
                ((result_w // 2 - space // 2) * 4, (result_h - space) * 4),
            ),
            outline=border_color,
            width=border_width * 4,
        )
        draw.rectangle(
            (
                ((result_w // 2 + space // 2) * 4, space * 4),
                ((result_w - space) * 4, (result_h - space) * 4),
            ),
            outline=border_color,
            width=border_width * 4,
        )
        draw.ellipse(
            (
                ((result_w // 2 - center_circle_radius) * 4, (result_h // 2 - center_circle_radius) * 4),
                (result_w // 2 + center_circle_radius) * 4,
                (result_h // 2 + center_circle_radius) * 4,
            ),
            outline=border_color,
            width=border_width * 4,
        )
        draw.ellipse(
            (
                (result_w // 2 - center_circle_radius + border_width) * 4,
                (result_h // 2 - center_circle_radius + border_width) * 4,
                (result_w // 2 + center_circle_radius - border_width) * 4,
                (result_h // 2 + center_circle_radius - border_width) * 4,
            ),
            fill=(0, 0, 0, 0),
        )
        draw.rectangle(
            (((result_w // 2 - space // 2) * 4, 0), ((result_w // 2 + space // 2) * 4, result_h * 4)), fill=(0, 0, 0, 0)
        )
        borders = borders.resize((borders.size[0] // 4, borders.size[1] // 4), resample=Image.Resampling.LANCZOS)

        suppress_center = Image.new("RGBA", (center_circle_radius * 2 * 4,) * 2, (0, 0, 0, 0))  # type: ignore
        draw = ImageDraw.Draw(suppress_center)
        draw.ellipse(((0, 0), (suppress_center.size[0],) * 2), fill=(0, 0, 0))  # type: ignore
        suppress_center = suppress_center.resize(
            (center_circle_radius * 2,) * 2,  # type: ignore
            resample=Image.Resampling.LANCZOS,
        )

        result.paste(images[0], (space + border_width, space + border_width))
        result.paste(images[1], (result_w - image_w - space - border_width, result_h - image_h - space - border_width))
        result.paste(
            (0, 0, 0, 0),
            (result_w // 2 - center_circle_radius, result_h // 2 - center_circle_radius),
            mask=suppress_center,
        )
        result.paste(borders, mask=borders)
        result.paste(plus, (result.size[0] // 2 - plus.size[0] // 2, result.size[1] // 2 - plus.size[1] // 2), plus)

        buffer = BytesIO()
        result.save(buffer, "PNG")
        buffer.seek(0)  # after the file is written, the "cursor" is positioned to the end
        return buffer

    def get_random_level(self) -> tuple[BytesIO, Level]:  # nosec
        level = random.choice(self.levels)
        images = self.load_images_level(level["rid"])
        return self.generate_image_assembly(images), level

    @app_commands.command(description='Jouer à "Mot Pour 2 Indications " !')
    async def mp2i_game(self, inter: Interaction) -> None:
        embed = response_constructor(ResponseType.info, "MP2I game !")["embed"]
        image, level = self.get_random_level()
        file = discord.File(image, filename="image.png")
        embed.set_image(url="attachment://image.png")

        embed.description = " ".join("**\\_**" for _ in range(len(level["ctl"])))

        await inter.response.send_message(
            embed=embed, file=file, view=MP2IGameView(inter.user, level["ctl"], embed, inter)
        )


class MP2IGameView(ui.View):
    def __init__(
        self, user: discord.User | discord.Member, word: str, embed: discord.Embed, original_inter: Interaction
    ):
        self.hints: set[int] = set()
        self.word = word
        self.embed = embed
        self.user = user
        self.original_inter = original_inter
        super().__init__(timeout=180)

    async def interaction_check(self, inter: Interaction) -> bool:
        if inter.user.id != self.user.id:
            await inter.response.send_message(
                **response_constructor(ResponseType.error, "Vous n'êtes pas à l'origine du jeu"), ephemeral=True
            )
            return False
        return True

    @ui.button(label="Devine !", style=discord.ButtonStyle.green)
    async def guess(self, inter: Interaction, button: ui.Button[Self]) -> None:
        await inter.response.send_modal(MP2IGameModalGuess(self))

    @ui.button(label="Indice", emoji="💡", style=discord.ButtonStyle.blurple)
    async def hint(self, inter: Interaction, button: ui.Button[Self]):
        if len(self.word) - len(self.hints) <= 3:
            await inter.response.send_message("3 lettres à trouver, c'est pas la mort !", ephemeral=True)
            return
        if len(self.hints) >= 3:
            await inter.response.send_message("Je vais pas donner tout le mot non plus !", ephemeral=True)
            return

        index = random.choice(tuple(set(range(len(self.word))) - self.hints))
        self.hints.add(index)

        self.embed.description = " ".join(
            "**\\_**" if i not in self.hints else f"**{l}**" for i, l in enumerate(self.word)
        )

        await inter.response.edit_message(embed=self.embed)

    @ui.button(label="Pourquoi", emoji="❓", style=discord.ButtonStyle.blurple)
    async def why(self, inter: Interaction, button: ui.Button[Self]) -> None:
        await inter.response.send_message(
            content=(
                "Ce bot a un repo Github (trouvable sur son profile), et dessus, il y a une présentation du bot.\n"
                "J'ai demandé, dans la première partie, à une intelligence artificielle de le présenter, et... "
                "elle m'a sortie tout simplement que **MP2I** signifiait : **M**ot **P**our **2** **I**mages !\n\n"
                "Ainsi le jeu est simple : il y a 2 images, et il faut trouver le mot associé ! Il fallait bien donner "
                "raison à cette pauvre IA...\n\n"
                "Enjoy !"
            ),
            ephemeral=True,
        )

    async def disable_all_buttons(self, apply: bool = False) -> None:
        btn: Any  # we can't force type to be Button, so we use Any (don't want to cast or add conditions... )
        for btn in self.children:
            btn.disabled = True
        if apply:
            await self.original_inter.edit_original_response(view=self)

    async def set_desc_fail(self, apply: bool = False) -> None:
        desc = cast(str, self.embed.description)
        desc += f"\nLe mot était **{self.word}**. Il n'a pas été trouvé..."
        self.embed.description = desc

        if apply:
            await self.original_inter.edit_original_response(embed=self.embed)

    async def set_desc_win(self, apply: bool = False) -> None:
        desc = cast(str, self.embed.description)
        desc += f"\nLe mot était **{self.word}**. Il a été trouvé !"
        self.embed.description = desc

        if apply:
            await self.original_inter.edit_original_response(embed=self.embed)

    async def on_timeout(self) -> None:
        await self.disable_all_buttons()
        await self.set_desc_fail()
        await self.original_inter.edit_original_response(embed=self.embed, view=self)

    async def stop_view(self, win: bool) -> None:
        self.stop()
        await self.disable_all_buttons()
        if win:
            await self.set_desc_win()
        else:
            await self.set_desc_fail()
        await self.original_inter.edit_original_response(embed=self.embed, view=self)


class MP2IGameModalGuess(ui.Modal, title="Quel est le mot ?"):
    response: ui.TextInput[Self] = ui.TextInput(label="Réponse :")

    def __init__(self, parent: MP2IGameView) -> None:
        self.response.placeholder = " ".join("_" if i not in parent.hints else l for i, l in enumerate(parent.word))
        self.response.max_length = len(parent.word)
        self.response.min_length = len(parent.word)
        self.parent = parent
        super().__init__(timeout=180)

    async def on_submit(self, inter: Interaction, /) -> None:
        if self.response.value.lower() == self.parent.word.lower():
            await inter.response.send_message(
                f"Bravo {inter.user.mention}! Tu as trouvé la réponse ! Le mot était {self.parent.word}.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            await self.parent.stop_view(True)
        else:
            await inter.response.send_message(
                f"Euh... {inter.user.mention} t'as vraiment cru que le mot était {self.response.value.upper()} ??\nComment t'es éclaté, c'était évident que le mot était {self.parent.word}...",
                allowed_mentions=discord.AllowedMentions.none(),  # don't ping the user
            )
            await self.parent.stop_view(False)


async def setup(bot: MP2IBot):
    await bot.add_cog(MP2IGame(bot))
