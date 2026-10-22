"""Ready check poll with buttons for the Dota 2 Gamers role in one specific server."""
from __future__ import annotations

import asyncio
import re

import discord
from discord.ext import commands

READYCHECK_GUILD_ID = 149264038017105920
DOTA_ROLE_ID = 1240097702864490507

READY_LINE = re.compile(r"^READY \(\d+\): ?(.*)$", re.MULTILINE)
NOT_READY_LINE = re.compile(r"^NOT READY \(\d+\): ?(.*)$", re.MULTILINE)


def _names(line: str) -> set[str]:
    return {name for name in line.split(", ") if name}


def parse_state(content: str) -> tuple[set[str], set[str]]:
    """Recover (ready, not_ready) names from a ready check message, so buttons survive restarts."""
    ready = READY_LINE.search(content)
    not_ready = NOT_READY_LINE.search(content)
    return _names(ready.group(1) if ready else ""), _names(not_ready.group(1) if not_ready else "")


def render(role_mention: str, ready: set[str], not_ready: set[str]) -> str:
    ready_list, not_ready_list = sorted(ready), sorted(not_ready)
    return (f"READY CHECK {role_mention}\n"
            f"READY ({len(ready_list)}): {', '.join(ready_list)}\n"
            f"NOT READY ({len(not_ready_list)}): {', '.join(not_ready_list)}")


def toggle(username: str, chosen: set[str], other: set[str]) -> None:
    """Clicking your current answer again clears it; otherwise switch to the clicked answer."""
    if username in chosen:
        chosen.discard(username)
    else:
        chosen.add(username)
        other.discard(username)


class ReadyCheckView(discord.ui.View):
    """Persistent view handling the buttons on every ready check message.

    State lives in memory (keyed by message id) so simultaneous clicks can't overwrite each
    other; after a restart it is rebuilt from the message text, so old polls keep working.
    """

    _states: dict[int, tuple[set[str], set[str]]] = {}
    _locks: dict[int, asyncio.Lock] = {}

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Ready", style=discord.ButtonStyle.green, custom_id="ready_button")
    async def ready_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._handle(interaction, ready_clicked=True)

    @discord.ui.button(label="Not Ready", style=discord.ButtonStyle.red, custom_id="not_ready_button")
    async def not_ready_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._handle(interaction, ready_clicked=False)

    async def _handle(self, interaction: discord.Interaction, ready_clicked: bool) -> None:
        message = interaction.message
        if message is None:
            await interaction.response.defer()
            return
        async with self._locks.setdefault(message.id, asyncio.Lock()):
            if message.id not in self._states:
                self._states[message.id] = parse_state(message.content)
            ready, not_ready = self._states[message.id]
            username = interaction.user.display_name
            if ready_clicked:
                toggle(username, ready, not_ready)
            else:
                toggle(username, not_ready, ready)
            role = message.guild.get_role(DOTA_ROLE_ID) if message.guild else None
            role_mention = role.mention if role else "@Dota 2 Gamers"
            await interaction.response.edit_message(content=render(role_mention, ready, not_ready))


class ReadyCheck(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def readycheck(self, ctx: commands.Context) -> None:
        """Create a ready check poll for Dota 2 Gamers"""
        if ctx.guild is None or ctx.guild.id != READYCHECK_GUILD_ID:
            return
        dota_role = ctx.guild.get_role(DOTA_ROLE_ID)
        if dota_role is None:
            await ctx.send("Could not find the @Dota 2 Gamers role!")
            return
        await ctx.send(render(dota_role.mention, set(), set()), view=ReadyCheckView())
