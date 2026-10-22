"""Guess-the-flag game (single player and first-to-N multiplayer)."""
from __future__ import annotations

import asyncio
import logging
import random

import discord
from discord.ext import commands

from modules import net
from modules.config import MODULES_DIR
from modules.discord_utils import image_to_file, safe_delete
from modules.games.stats import ScoreStore
from modules.image_input import ImageDecodeError, decode_image
from modules.storage import ReloadingJsonFile

log = logging.getLogger(__name__)

ROUND_SECONDS = 15
DEFAULT_POINTS_TO_WIN = 5
MIN_POINTS_TO_WIN, MAX_POINTS_TO_WIN = 2, 30
MAX_MISSED_ROUNDS = 3

# Game difficulty -> which flags.json "difficulty" values are in play.
# 0 default, 1 easy, 2 normal, 3 hard, 4 states, 5 expert, 6 all, 7 japanese prefectures
DIFFICULTY_POOLS: dict[int, set[int] | None] = {
    0: {1, 2, 3}, 1: {1}, 2: {2}, 3: {3}, 4: {4}, 5: {4, 5}, 6: None, 7: {7},
}
DIFFICULTY_WORDS = {
    "easy": 1, "e": 1, "normal": 2, "n": 2, "hard": 3, "h": 3, "states": 4, "s": 4,
    "expert": 5, "extreme": 5, "x": 5, "all": 6, "a": 6, "japan": 7, "j": 7,
}
SUBJECT = {0: "country", 1: "country", 2: "country", 3: "country", 4: "flag", 5: "flag", 6: "flag",
           7: "Japanese Prefecture"}

MSG_ERROR = "Sorry, something went wrong! Please try again"

_flags = ReloadingJsonFile(MODULES_DIR / "flags.json")


def difficulty_from_arg(arg: str) -> int:
    return DIFFICULTY_WORDS.get(arg, 0)


def pick_flag(difficulty: int, rng: random.Random | None = None) -> dict:
    flags = _flags.load()
    pool = DIFFICULTY_POOLS.get(difficulty, DIFFICULTY_POOLS[0])
    candidates = [flag for flag in flags if pool is None or flag["difficulty"] in pool] or flags
    return (rng or random).choice(candidates)


def flag_names(flag: dict) -> list[str]:
    return flag["name"] if isinstance(flag["name"], list) else [flag["name"]]


async def _load_flag(difficulty: int) -> tuple[dict, discord.File] | None:
    """Pick a flag and download its image; None if the download failed."""
    flag = pick_flag(difficulty)
    try:
        data = await net.get_bytes(flag["url"])
        file = await asyncio.to_thread(lambda: image_to_file(decode_image(data), "flag.png"))
    except (net.FetchError, ImageDecodeError, OSError) as e:
        log.warning("Couldn't load flag %s: %s", flag["url"], e)
        return None
    return flag, file


def _answer_check(channel: discord.abc.Messageable, flag: dict):
    answers = {name.lower() for name in flag_names(flag)}

    def check(m: discord.Message) -> bool:
        return m.channel == channel and m.content.lower() in answers

    return check


def _round_embed(subject: str) -> discord.Embed:
    embed = discord.Embed(title=f"You have {ROUND_SECONDS} seconds to guess the {subject}!",
                          colour=discord.Color.gold())
    embed.set_image(url="attachment://flag.png")
    return embed


async def flag_guesser(ctx: commands.Context, scores: ScoreStore, difficulty: int = 0) -> None:
    subject = SUBJECT[difficulty]
    loaded = await _load_flag(difficulty)
    if loaded is None:
        await ctx.send(MSG_ERROR)
        return
    flag, file = loaded
    name = flag_names(flag)[0]
    await ctx.send(embed=_round_embed(subject), file=file)
    try:
        msg = await ctx.bot.wait_for("message", check=_answer_check(ctx.channel, flag), timeout=ROUND_SECONDS)
    except asyncio.TimeoutError:
        await ctx.send("Sorry, nobody got the " + subject + " correct! The correct answer was: " + name)
        return
    await ctx.send("Good job " + msg.author.mention + "! The " + subject + " was " + name)
    scores.record_flag_win(msg.author, difficulty, name)


async def flag_guesser_multi(ctx: commands.Context, scores: ScoreStore, difficulty: int = 0,
                             points_to_win: int = DEFAULT_POINTS_TO_WIN) -> None:
    points_to_win = max(min(points_to_win, MAX_POINTS_TO_WIN), MIN_POINTS_TO_WIN)
    subject = SUBJECT[difficulty]
    await ctx.send(f"Get ready to guess the flag! The first person to correctly guess {points_to_win} flags wins!")

    points: dict[int, int] = {}
    players: dict[int, discord.abc.User] = {}
    missed_in_a_row = 0
    round_message: discord.Message | None = None
    round_number = 1
    while True:
        loaded = await _load_flag(difficulty)
        if loaded is None:
            await ctx.send(MSG_ERROR)
            return
        flag, file = loaded
        name = flag_names(flag)[0]

        await safe_delete(round_message)
        embed = _round_embed(subject)
        embed.set_footer(text=f"Round {round_number}, First to {points_to_win} wins!")
        round_message = await ctx.send(embed=embed, file=file)

        winner = None
        try:
            msg = await ctx.bot.wait_for("message", check=_answer_check(ctx.channel, flag), timeout=ROUND_SECONDS)
        except asyncio.TimeoutError:
            await ctx.send(f"Sorry, nobody got the {subject} correct! The correct answer was: {name}")
            missed_in_a_row += 1
            if missed_in_a_row == MAX_MISSED_ROUNDS:
                await ctx.send("If nobody gets this next one correct, the game will end!")
            if missed_in_a_row > MAX_MISSED_ROUNDS:
                await ctx.send("Game over! Nobody wins :(")
                return
        else:
            missed_in_a_row = 0
            player = msg.author
            await ctx.send(f"Good job {player.mention}! The {subject} was {name}")
            scores.record_flag_win(player, difficulty, name, multiplayer_round=True)
            players[player.id] = player
            points[player.id] = points.get(player.id, 0) + 1
            if points[player.id] >= points_to_win:
                await ctx.send(f"Congratulations {player.mention}! You are our winner!")
                scores.record_flag_game_win(player)
                winner = player

        scoreboard = discord.Embed(title="Scoreboard!", colour=discord.Color.blurple())
        for player_id, score in sorted(points.items(), key=lambda item: item[1], reverse=True):
            scoreboard.add_field(name=players[player_id].name, value=score, inline=False)
        await ctx.send(embed=scoreboard)
        if winner is not None:
            return
        round_number += 1
