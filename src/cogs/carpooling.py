from __future__ import annotations

import asyncio
import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import partial
from typing import TYPE_CHECKING, Any, Self, cast
from zoneinfo import ZoneInfo

from discord import (
    ActionRow,
    AllowedMentions,
    Button as ButtonComponent,
    ButtonStyle,
    ChannelType,
    Embed,
    Guild,
    Message,
    Object,
    SelectOption,
    TextChannel,
    Thread,
    app_commands,
    ui,
)
from discord.ext import commands
from discord.interactions import Interaction

from core.constants import CARPOOLING_CHANNEL, GUILD_ID
from core.errors import BaseError

if TYPE_CHECKING:
    from re import Match

    from discord import Interaction

    from bot import FISABot

    type PartialContextT = partial[Context]


PREDEFINED_DESTINATIONS = {"Carrefour": 1284288507086503937}
TZ = ZoneInfo("Europe/Paris")
NO_PASSENGERS_STRING = "Aucun inscrit"


@dataclass()
class Context:
    user: int
    destination: str
    number_of_passengers: int
    date: datetime
    passengers: set[int] = field(default_factory=set)
    thread_id: int | None = None

    def replace(self, **kwargs: dict[str, Any]) -> Context:
        return dataclasses.replace(self, **kwargs)

    async def getch_thread(self, bot: FISABot):
        guild = cast(Guild, bot.get_guild(GUILD_ID))

        if self.thread_id is None:
            raise ValueError("context.thread_id shouldn't be None !")  # noqa: TRY003

        thread = guild.get_thread(self.thread_id) or await guild.fetch_channel(self.thread_id)
        if not isinstance(thread, Thread):
            raise BaseError

        return thread

    @classmethod
    async def from_message(cls, message: Message):
        if not message.components or not isinstance(message.components[0], ActionRow):
            raise ValueError

        button = message.components[0].children[0]
        pattern = DynamicTogglePresence.__discord_ui_compiled_template__
        if (
            not isinstance(button, ButtonComponent)
            or button.custom_id is None
            or (match := pattern.match(button.custom_id)) is None
        ):
            raise ValueError

        return await Context.from_match(message, match)

    @classmethod
    async def from_match(cls, message: Message, match: Match[str]):
        return Context(
            user=int(match["user"]),
            destination=match["destination"],
            number_of_passengers=int(match["number_of_passengers"]),
            date=datetime.fromtimestamp(int(match["date"]), TZ),
            passengers=Carpooling.passengers_from_message(message),
            thread_id=int(match["thread_id"]),
        )


class Carpooling(commands.Cog):
    def __init__(self, bot: FISABot):
        self.bot = bot
        self.bot.add_dynamic_items(DynamicTogglePresence)
        self.bot.add_view(CarpoolingView(self, None))

        self.setup_task: None | asyncio.Task[Any] = None
        self.currents_carpooling: dict[int, tuple[Context, asyncio.Task[None]]] = {}

    async def cog_load(self) -> None:
        def cleanup_task(task: asyncio.Task[Any]):
            self.setup_task = None

        self.setup_task = asyncio.create_task(self.load_carpooling_task())
        self.setup_task.add_done_callback(cleanup_task)

    async def load_carpooling_task(self):
        await self.bot.wait_until_ready()
        channel = cast(TextChannel, self.bot.get_channel(CARPOOLING_CHANNEL))
        async for message in channel.history():  # all the active carpooling should be present in the last 100 messages
            try:
                context = await Context.from_message(message)
            except Exception:  # noqa: S112
                continue
            if context.date < datetime.now(TZ):
                continue
            self.monitor_carpooling(message.id, context)

    def monitor_carpooling(self, message_id: int, context: Context):
        async def carpooling_reminders():
            now = datetime.now(TZ)
            if context.date - now > timedelta(minutes=15):
                await asyncio.sleep((context.date - now - timedelta(minutes=15)).total_seconds())
                await self.alert(context, f"Départ dans 15 minutes ! (<t:{int(context.date.timestamp())}:R>)")
                await asyncio.sleep(timedelta(minutes=15).total_seconds())
            else:
                await asyncio.sleep((context.date - now).total_seconds())

            await self.alert(context, "Départ !")

        task = asyncio.create_task(carpooling_reminders())
        self.currents_carpooling[message_id] = (context, task)

    @staticmethod
    def passengers_from_message(message: Message) -> set[int]:
        embed = message.embeds[0]
        field = embed.fields[3]
        value = cast(str, field.value)
        if value == NO_PASSENGERS_STRING:
            return set()
        return {int(line[2:-1]) for line in value.splitlines()}

    @staticmethod
    def build_embed(context: Context):
        embed = Embed(
            title=f"Covoiturage vers {context.destination} !",
            color=0x57F287 if len(context.passengers) < context.number_of_passengers else 0xED4245,
        )
        embed.add_field(name="Destination", value=context.destination)
        timestamp = int(context.date.timestamp())
        embed.add_field(name="Date", value=f"<t:{timestamp}:f> (<t:{timestamp}:R>)")
        embed.add_field(name="Conducteur", value=f"<@{context.user}>")

        embed.add_field(
            name=f"Passagers : {len(context.passengers)}/{context.number_of_passengers}",
            value="\n".join(f"<@{id}>" for id in context.passengers) if context.passengers else NO_PASSENGERS_STRING,
            inline=False,
        )

        return embed

    async def new_carpooling(self, channel: TextChannel, context: Context):
        if context.destination in PREDEFINED_DESTINATIONS:
            content = f"<@&{PREDEFINED_DESTINATIONS[context.destination]}>"
        else:
            content = None
        thread = await channel.create_thread(
            name=f"Covoiturage vers {context.destination[:30]} !", type=ChannelType.private_thread
        )
        context.thread_id = thread.id
        message = await channel.send(
            embed=self.build_embed(context),
            view=CarpoolingView(self, context),
            content=content,
            allowed_mentions=AllowedMentions(roles=True),
        )
        await thread.add_user(Object(context.user))
        self.monitor_carpooling(message.id, context)

    async def update_carpooling(self, message: Message, context: Context, alert_message: str):
        await message.edit(embed=self.build_embed(context), view=CarpoolingView(self, context))
        await self.alert(context, alert_message)

    async def alert(self, context_or_thread: Context | Thread, alert_message: str, /):
        if isinstance(context_or_thread, Thread):
            thread = context_or_thread
        else:
            thread = await context_or_thread.getch_thread(self.bot)

        await thread.send(f"@everyone\n{alert_message}", allowed_mentions=AllowedMentions(everyone=True))

    async def cancel_carpooling(self, message: Message, context: Context):
        thread = await context.getch_thread(self.bot)
        await message.delete()
        await self.alert(thread, "Ce covoiturage a été annulé ! Je vous invite à quitter ce fil.")

    @app_commands.command()
    async def init_carpooling(self, inter: Interaction):
        await inter.response.send_message(
            view=CarpoolingDestination(partial(Context, user=inter.user.id)), ephemeral=True
        )


class CarpoolingViewMixin:
    edit_mode = False

    def set_edit_mode(self, message: Message, context: Context):
        self.edit_mode = True
        self.original_message = message
        self.old_context = context

    def get_cog(self, bot: commands.Bot | Any) -> Carpooling:
        # We use Any, because inter.client is used in this function, and inter.client is typed as discord.Client (while it is a commands.Bot instance here).
        # Moreover, because ClientT is covariant, we can't use commands.Bot in Interaction generics.
        return cast(Carpooling, bot.get_cog(Carpooling.__cog_name__))


class CarpoolingViewBase(ui.View, CarpoolingViewMixin):
    def __init__(self, context: PartialContextT):
        self.context = context
        super().__init__(timeout=600)


class CarpoolingModalBase(ui.Modal, CarpoolingViewMixin):
    def __init__(self, context: PartialContextT):
        self.context = context
        super().__init__()


class NewCarpoolingView(ui.View):
    def __init__(self, cog: Carpooling):
        super().__init__(timeout=None)
        self.cog = cog

    @ui.button(label="Nouveau covoiturage", custom_id="new_carpooling")
    async def new_carpooling(self, inter: Interaction, btn: ui.Button[Self]):
        await inter.response.send_message(
            ephemeral=True, view=CarpoolingDestination(partial(Context, user=inter.user.id))
        )


class CarpoolingDestination(CarpoolingViewBase):
    @ui.select(
        placeholder="Où vas-tu ?",
        options=[SelectOption(label=destination) for destination in [*PREDEFINED_DESTINATIONS, "Autre"]],
        max_values=1,
    )
    async def select_destination(self, inter: Interaction, select: ui.Select[Self]):
        value = select.values[0]
        if value in PREDEFINED_DESTINATIONS:
            self.context = partial(self.context, destination=value)
            await inter.response.edit_message(view=CarpoolingNumberOfPassengers(self.context))

        else:
            await inter.response.send_modal(CarpoolingCustomDestination(self.context))


class CarpoolingCustomDestination(CarpoolingModalBase, title="Où vas-tu ?"):
    destination = ui.TextInput[Self](label="Destination")

    async def on_submit(self, inter: Interaction):
        self.context = partial(self.context, destination=self.destination.value.replace(":", ""))
        await inter.response.edit_message(view=CarpoolingNumberOfPassengers(self.context))


class CarpoolingNumberOfPassengers(CarpoolingViewBase):
    @ui.select(
        placeholder="Combien de passagers peux-tu prendre ?",
        options=[SelectOption(label=str(i)) for i in range(1, 6)],
        max_values=1,
    )
    async def wip(self, inter: Interaction, select: ui.Select[Self]):
        value = int(select.values[0])
        self.context = partial(self.context, number_of_passengers=value)
        await inter.response.send_modal(CarpoolingDate(self.context))


class CarpoolingDate(CarpoolingModalBase, title="Quand pars-tu ?"):
    date = ui.TextInput[Self](label="Format: dd/mm HH:MM ou HH:MM", max_length=11, min_length=4)

    def __init__(self, context: PartialContextT, default: str | None = None):
        super().__init__(context)
        self.date.default = default

    async def on_submit(self, inter: Interaction) -> None:
        now = datetime.now(TZ)

        async def send_error(message: str):
            await inter.response.edit_message(
                content=message,
                view=CarpoolingDateRetry(self.context, self.date.value),
            )

        try:
            date = datetime.strptime(self.date.value, "%d/%m %H:%M").replace(tzinfo=TZ)
            if (date := date.replace(year=now.year)) < now:
                date = date.replace(year=now.year + 1)
        except ValueError:
            try:
                date = datetime.strptime(self.date.value, "%H:%M").replace(
                    year=now.year,
                    month=now.month,
                    day=now.day,
                    tzinfo=TZ,
                )
            except ValueError:
                await send_error(
                    f"`{self.date.value[:1800]}` n'est pas une date valide ! Des exemples sont : `{now:%d/%m %H:%M}`, `{now:%H:%M}`"
                )
                return
        if date < now:
            await send_error(f"Vous ne pouvez pas choisir une date antérieur à maintenant ! ({date:%d/%m %H:%M})")
            return
        if date - now > timedelta(days=30 * 2):
            await send_error("Vous ne pouvez pas créer un covoiturage à plus de 2 mois !")
            return

        self.context = partial(self.context, date=date)
        await inter.response.defer()
        cog = self.get_cog(cast(commands.Bot, inter.client))
        if self.edit_mode:
            new_context = self.context()
            await cog.update_carpooling(
                self.original_message,
                new_context,
                f"La date de ce covoiturage a été décalé du <t:{int(self.old_context.date.timestamp())}:f> au <t:{int(new_context.date.timestamp())}:f>",
            )
        else:
            await cog.new_carpooling(cast(TextChannel, inter.channel), self.context())


class CarpoolingDateRetry(CarpoolingViewBase):
    def __init__(self, context: PartialContextT, default: str):
        super().__init__(context)
        self.default = default

    @ui.button(label="Recommencer")
    async def retry(self, inter: Interaction, button: ui.Button[Self]):
        await inter.response.send_modal(CarpoolingDate(self.context, self.default))


class DynamicTogglePresence(
    ui.DynamicItem[ui.Button["CarpoolingView"]],
    template=r"carpooling_toggle:(?P<user>\d+):(?P<destination>[^:]+):(?P<number_of_passengers>\d+):(?P<date>\d+):(?P<thread_id>\d+)",
):
    def __init__(self, context: Context | None):
        if context is None:
            super().__init__(ui.Button(custom_id="carpooling_toggle:0:a:0:0:0"))  # persistant
            return
        self.context = context
        thread_id = cast(int, context.thread_id)
        super().__init__(
            ui.Button(
                label="Rejoindre / Se retirer",
                custom_id=f"carpooling_toggle:{context.user}:{context.destination}:{context.number_of_passengers}:{int(context.date.timestamp())}:{thread_id}",
                row=0,
                style=ButtonStyle.blurple,
            )
        )

    @classmethod
    async def from_custom_id(
        cls, interaction: Interaction, item: ui.Item[CarpoolingView], match: Match[str], /
    ) -> Self:
        if interaction.message is None:
            raise BaseError
        context = await Context.from_match(interaction.message, match)
        return cls(context)

    async def callback(self, interaction: Interaction) -> Any:
        if interaction.message is None or self.context.thread_id is None:
            raise BaseError

        if interaction.user.id == self.context.user:
            await interaction.response.send_message(
                "Vous ne pouvez pas conduire et être passager :eyes:", ephemeral=True
            )
            return

        guild = cast(Guild, interaction.guild)

        thread = guild.get_thread(self.context.thread_id) or await guild.fetch_channel(self.context.thread_id)
        if not isinstance(thread, Thread):
            raise BaseError

        if interaction.user.id in self.context.passengers:
            self.context.passengers.remove(interaction.user.id)
            await thread.remove_user(interaction.user)
        else:
            self.context.passengers.add(interaction.user.id)
            await thread.add_user(interaction.user)
        await interaction.response.edit_message(embed=Carpooling.build_embed(self.context))


class CarpoolingView(ui.View):
    def __init__(self, cog: Carpooling, context: Context | None):
        super().__init__(timeout=None)
        self.dynamic_toggle = DynamicTogglePresence(context)
        self.add_item(self.dynamic_toggle)

        # For ordering
        self.remove_item(self.edit_carpooling)
        self.add_item(self.edit_carpooling)

        self.cog = cog

    async def get_context(self, inter: Interaction) -> Context:
        if inter.message is None:
            raise BaseError
        return await Context.from_message(inter.message)

    @ui.button(label="Nouveau covoiturage", custom_id="new_carpooling", style=ButtonStyle.green, row=1)
    async def new_carpooling(self, inter: Interaction, btn: ui.Button[Self]):
        await inter.response.send_message(
            ephemeral=True, view=CarpoolingDestination(partial(Context, user=inter.user.id))
        )

    @ui.button(label="Modifier le covoiturage", custom_id="edit_carpooling", style=ButtonStyle.gray, row=0)
    async def edit_carpooling(self, inter: Interaction, btn: ui.Button[Self]):
        context = await self.get_context(inter)
        if inter.user.id != context.user:
            await inter.response.send_message("Seul le conducteur peut modifier le covoiturage !", ephemeral=True)
            return

        await inter.response.send_message(
            ephemeral=True, view=EditCarpoolingView(context, cast(Message, inter.message))
        )


class EditCarpoolingView(CarpoolingViewBase):
    def __init__(self, context: Context, message: Message):
        self.old_context = context
        self.message = message
        super().__init__(context=partial(context.replace))

    @ui.select(
        placeholder="Que souhaites-tu modifier ?",
        options=[
            SelectOption(label=label, value=value, description=description)
            for label, value, description in [
                ("Changer la date", "change_date", "Pour modifier la date du covoiturage"),
                ("Annuler", "delete", "Pour annuler le covoiturage"),
            ]
        ],
    )
    async def edit(self, inter: Interaction, select: ui.Select[Self]):
        match select.values[0]:
            case "change_date":
                modal = CarpoolingDate(self.context, default=self.old_context.date.strftime("%d/%m %H:%M"))
                modal.set_edit_mode(self.message, self.old_context)
                await inter.response.send_modal(modal)
            case "delete":
                view = ConfirmCarpoolingDeletion(self.context)
                view.set_edit_mode(self.message, self.old_context)
                await inter.response.edit_message(view=view)
            case _:
                pass


class ConfirmCarpoolingDeletion(CarpoolingViewBase):
    @ui.button(label="Confirmer la suppression", style=ButtonStyle.red)
    async def delete(self, inter: Interaction, button: ui.Button[Self]):
        await inter.response.defer()
        await self.get_cog(inter.client).cancel_carpooling(self.original_message, self.old_context)


async def setup(bot: FISABot):
    await bot.add_cog(Carpooling(bot))
