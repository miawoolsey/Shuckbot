"""Guess-the-hex-code colour game (single player and multiplayer)."""
from __future__ import annotations

import asyncio
import math
import random
import re
import time

import discord
import numpy as np
from discord.ext import commands
from PIL import Image

from modules.discord_utils import image_to_file, send_long

# colormath 3.0 still calls np.asscalar, which numpy removed in 1.23.
if not hasattr(np, "asscalar"):
    np.asscalar = lambda a: a.item()

from colormath.color_conversions import convert_color  # noqa: E402
from colormath.color_diff import delta_e_cmc  # noqa: E402
from colormath.color_objects import LabColor, sRGBColor, XYZColor  # noqa: E402

SIZE = 150
MAX_MULTIPLAYER_SECONDS = 60
DEFAULT_MULTIPLAYER_SECONDS = 15
HISTORY_LIMIT = 50
HEX_CODE = re.compile(r"[0-9a-fA-F]{6}")


def random_hex() -> str:
    return f"{random.getrandbits(24):06x}"


def _rgb(hex_code: str) -> tuple[int, int, int]:
    return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)


def _to_lab(rgb: tuple[int, int, int]) -> LabColor:
    srgb = sRGBColor(*(channel / 255 for channel in rgb))
    return convert_color(convert_color(srgb, XYZColor), LabColor)


def calculate_score(guess: str, actual: str) -> float:
    """0-100 score based on the CMC colour difference between two hex codes."""
    difference = delta_e_cmc(_to_lab(_rgb(guess)), _to_lab(_rgb(actual)))
    score = (100 - (difference - 2) ** 0.7 * (23 / 3)) if difference > 2 else 100
    return max(score, 0)


def swatch(hex_code: str) -> Image.Image:
    return Image.new("RGB", (SIZE, SIZE), "#" + hex_code)


def result_image(actual: str, guesses: list[str]) -> Image.Image:
    """Actual colour on the left; guesses stacked on the right half (best first)."""
    img = swatch(actual)
    for i, guess in enumerate(guesses):
        img.paste(Image.new("RGB", (SIZE // 2, SIZE), "#" + guess), (SIZE // 2, i * SIZE // len(guesses)))
    return img


async def colour_guesser(ctx: commands.Context, letter: str = "") -> None:
    actual = random_hex()
    mention = ctx.author.mention
    await ctx.send(mention + ", here is your colo" + letter + "r! Try to guess its hex code!",
                   file=image_to_file(swatch(actual), "colourguess.png"))

    def check(m: discord.Message) -> bool:
        return m.author == ctx.author and m.channel == ctx.channel

    start = time.time()
    msg = await ctx.bot.wait_for("message", check=check)
    elapsed = time.time() - start

    guess = msg.content[1:] if msg.content.startswith("#") else msg.content
    if not HEX_CODE.fullmatch(guess):
        await ctx.send("Sorry, your answer was not formatted correctly! Your answer should just be the 6 digit "
                       "hexadecimal code for your guess, and nothing else! The actual colo" + letter + "r was "
                       + actual + " !")
        return

    score = calculate_score(guess, actual)
    plural = "" if score == 1 else "s"
    await ctx.send("The actual colo" + letter + "r was " + actual + "!\n" + mention + " got " + str(int(score))
                   + "/100 point" + plural + "\n" + "You took %.1f seconds to guess!" % elapsed,
                   file=image_to_file(result_image(actual, [guess]), "clrguessresult.png"))


async def colour_guesser_multi(ctx: commands.Context, letter: str = "",
                               game_time: int = DEFAULT_MULTIPLAYER_SECONDS) -> None:
    game_time = min(game_time, MAX_MULTIPLAYER_SECONDS)
    actual = random_hex()
    prompt = await ctx.send("Here is your colo" + letter + "r! Everyone try to guess its hex code!"
                            "\nYou have " + str(game_time) + " seconds...",
                            file=image_to_file(swatch(actual), "colourguess.png"))
    await asyncio.sleep(game_time)

    # Each player's most recent valid guess counts (history is newest first).
    latest_guess: dict[int, str] = {}
    async for message in ctx.channel.history(limit=HISTORY_LIMIT):
        if message.id == prompt.id:
            break
        if HEX_CODE.fullmatch(message.clean_content) and message.author.id not in latest_guess:
            latest_guess[message.author.id] = message.clean_content

    if not latest_guess:
        await ctx.send("Time out! Nobody guessed!")
        return

    results = [(user_id, guess, calculate_score(guess, actual)) for user_id, guess in latest_guess.items()]
    results.sort(key=lambda result: result[2], reverse=True)
    winner_id, _, winner_score = results[0]
    await ctx.send(f"The actual colo{letter}r was {actual}!\n<@{winner_id}>"
                   f" got {math.ceil(winner_score)}/100 points\n",
                   file=image_to_file(result_image(actual, [guess for _, guess, _ in results]), "clrguessresult.png"))
    await send_long(ctx.channel, "".join(
        f"{rank}. <@{user_id}>: {math.ceil(score)}/100 points (#{guess})\n"
        for rank, (user_id, guess, score) in enumerate(results, start=1)))
