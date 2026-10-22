"""Server prefix, ping and invite commands."""
from __future__ import annotations

import discord
from discord.ext import commands
from tinydb import Query

from modules.config import BASE_DIR, DEFAULT_PREFIX, Config
from modules.storage import open_db

Guild = Query()


class PrefixStore:
    """Per-server command prefixes, looked up from memory on every message."""

    def __init__(self) -> None:
        self._db = open_db(BASE_DIR / "prefixes.json")
        self._prefixes = {doc["id"]: doc["prefix"] for doc in self._db.all()}

    def get(self, guild_id: int | None) -> str:
        if guild_id is None:
            return DEFAULT_PREFIX
        return self._prefixes.get(guild_id, DEFAULT_PREFIX)

    def set(self, guild_id: int, prefix: str) -> None:
        self._db.upsert({"id": guild_id, "prefix": prefix}, Guild.id == guild_id)
        self._prefixes[guild_id] = prefix


class Core(commands.Cog):
    def __init__(self, bot: commands.Bot, config: Config, prefixes: PrefixStore) -> None:
        self.bot = bot
        self.config = config
        self.prefixes = prefixes

    @commands.command(aliases=["shuckbotprefix", "shuckprefix"])
    @commands.guild_only()
    async def prefix(self, ctx: commands.Context, *args: str) -> None:
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.administrator):
            await ctx.send("You need the **Manage Server** permission to do that.")
        elif len(args) != 1 or len(args[0]) > 1:
            await ctx.send("**Format**: ;prefix <single character>")
        elif not args[0].isascii():
            await ctx.send("You must choose an ASCII character!")
        else:
            self.prefixes.set(ctx.guild.id, args[0])
            await ctx.send("Set server prefix to \"" + args[0] + "\".")

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        start = discord.utils.utcnow()
        sent = await ctx.send("Measuring ping...")
        diff = sent.created_at - start
        await sent.edit(content="Pong! Shuckbot's ping is **" + str(int(diff.total_seconds() * 1000)) + "**ms.")

    @commands.command()
    async def invite(self, ctx: commands.Context) -> None:
        await ctx.send(self.config.invite_url)
