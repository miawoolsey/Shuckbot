"""Persistent per-user game statistics (modules/scores.json) plus the stats/leaderboard views.

File layout (kept compatible with the original bot)::

    {"<@user_id>": {"color": {}, "flag": {...}, "geography": {...}, "geoguesser": {...}}}
"""
from __future__ import annotations

import discord
from discord.ext import commands

from modules.config import MODULES_DIR
from modules.discord_utils import safe_delete
from modules.storage import JsonDocument

GAMES = ("color", "flag", "geography", "geoguesser")
STATS_FOOTER = "Stat collection started 3/23/2021"
LEADERBOARD_SIZE = 10


def user_key(user: discord.abc.Snowflake) -> str:
    return f"<@{user.id}>"


def _increment(stats: dict, key: str, amount: float = 1) -> None:
    stats[key] = stats.get(key, 0) + amount


def _running_mean(stats: dict, key: str, value: float, count: int) -> None:
    if count <= 1 or key not in stats:
        stats[key] = value
    else:
        stats[key] = (value + (count - 1) * stats[key]) / count


class ScoreStore:
    def __init__(self, path=MODULES_DIR / "scores.json") -> None:
        self._doc = JsonDocument(path, indent=4)

    @property
    def data(self) -> dict:
        return self._doc.data

    def _stats(self, key: str, game: str) -> dict:
        user = self.data.setdefault(key, {name: {} for name in GAMES})
        return user.setdefault(game, {})

    def record_flag_win(self, user: discord.abc.Snowflake, difficulty: int, flag_name: str,
                        multiplayer_round: bool = False) -> None:
        stats = self._stats(user_key(user), "flag")
        _increment(stats, f"difficulty_{difficulty}")
        _increment(stats.setdefault("flag", {}), flag_name)
        _increment(stats, "total")
        if multiplayer_round:
            _increment(stats, "rounds_won")
        self._doc.save()

    def record_flag_game_win(self, user: discord.abc.Snowflake) -> None:
        _increment(self._stats(user_key(user), "flag"), "games_won")
        self._doc.save()

    def record_geography(self, user: discord.abc.Snowflake, area: str, mode: str) -> None:
        stats = self._stats(user_key(user), "geography")
        combo = f"{area}_{mode}_"
        for key, value in (("area", area), ("mode", mode)):
            counts = stats.setdefault(key, {})
            _increment(counts, value)
            _increment(counts, combo)
        self._doc.save()

    def record_geoguesser(self, user: discord.abc.Snowflake, points: int, distance_km: float) -> None:
        stats = self._stats(user_key(user), "geoguesser")
        _increment(stats, "total")
        _increment(stats, "total_points", points)
        _increment(stats, "gold_stars", 1 if points == 5000 else 0)
        _increment(stats, "total_distance", distance_km)
        _running_mean(stats, "avg_pointsA", points, stats["total"])
        _running_mean(stats, "avg_distanceA", distance_km, stats["total"])
        self._doc.save()

    def flag_stats(self, user: discord.abc.Snowflake) -> dict:
        return self.data.get(user_key(user), {}).get("flag", {})


def _user_id(key: str) -> int | None:
    digits = key.strip("<@!>")
    return int(digits) if digits.isdigit() else None


async def _display_name(bot: commands.Bot, key: str) -> str:
    user_id = _user_id(key)
    if user_id is None:
        return key
    user = bot.get_user(user_id)
    if user is None:
        try:
            user = await bot.fetch_user(user_id)
        except discord.HTTPException:
            return key
    return user.name


async def show_stats(ctx: commands.Context, scores: ScoreStore, user: discord.abc.User, game: str) -> None:
    if game == "color":
        await ctx.send("Sorry! There are no stats for that game yet!")
        return
    if game == "geography":
        return  # no geography stats view exists yet
    stats = scores.flag_stats(user)
    if "total" not in stats:
        await ctx.send(f"{user.name} has not played this game yet!")
        return
    if game == "flag":
        embed = discord.Embed(title=f"Stats for user {user.name} for the Flag game", colour=discord.Colour.red())
        embed.set_footer(text=STATS_FOOTER)
        embed.add_field(name="Flags correctly guessed:", value=f"{stats['total']}")
        embed.add_field(name="Rounds won in multiplayer:", value=f"{stats.get('rounds_won', 0)}")
        embed.add_field(name="Games won in multiplayer:", value=f"{stats.get('games_won', 0)}")
    else:
        embed = discord.Embed(title=f"Stats for user {user.name}", colour=discord.Colour.red())
        embed.set_footer(text=f"{STATS_FOOTER}\nFor more stats, add the name of the game to your mesage!")
        embed.add_field(name="Flags correctly guessed:", value=f"{stats['total']}")
    await ctx.send(embed=embed)


async def show_leaderboard(ctx: commands.Context, scores: ScoreStore) -> None:
    sent = await ctx.send("Processing... (This may slow down the bot when it's called, so it might take a while)")
    embed = discord.Embed(title="Global Leaderboard", colour=discord.Colour.gold())
    embed.set_footer(text=STATS_FOOTER)
    for title, stat in (("__Total Flags__", "total"), ("__Flag Rounds Won__", "rounds_won"),
                        ("__Flag Games Won__", "games_won")):
        entries = [(user["flag"][stat], key) for key, user in scores.data.items()
                   if stat in user.get("flag", {})]
        entries.sort(key=lambda entry: entry[0], reverse=True)
        # Only the top entries need names, so at most 30 user lookups instead of one per player.
        lines = [f"{await _display_name(ctx.bot, key)}: {value}\n" for value, key in entries[:LEADERBOARD_SIZE]]
        embed.add_field(name=title, value="".join(lines) or "\u200b")
    await safe_delete(sent)
    await ctx.send(embed=embed)
