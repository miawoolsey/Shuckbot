"""Geography games: Japanese prefecture map quiz and a GeoGuessr-style location game."""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import discord
import geocoder
import numpy as np
from discord.ext import commands
from geopy import distance
from PIL import Image

from modules import net
from modules.config import ASSETS_DIR, MODULES_DIR
from modules.discord_utils import image_to_file
from modules.games.stats import ScoreStore
from modules.image_input import ImageDecodeError, decode_image
from modules.storage import ReloadingJsonFile

log = logging.getLogger(__name__)

MAP_ROUND_SECONDS = 15
GEOGUESSER_DEFAULT_SECONDS = 60
GEOGUESSER_MIN_SECONDS, GEOGUESSER_MAX_SECONDS = 10, 600
CONFIRM_WORDS = ("yes", "y", "confirm")
MAP_ZOOMS = ("13", "7", "2")
# Images from the now-dead rimgo.pussthecat.org mirror are bundled under assets/misc/.
BUNDLED_IMAGE_HOSTS = {"rimgo.pussthecat.org", "i.imgur.com", "imgur.com"}

_prefectures = ReloadingJsonFile(MODULES_DIR / "prefectures.json")
_locations = ReloadingJsonFile(MODULES_DIR / "geoguessing.json")


# --- prefecture map quiz -------------------------------------------------------------------

async def geography_game(ctx: commands.Context, scores: ScoreStore, area: str = "japan", mode: str = "map") -> None:
    area = area or "japan"
    mode = mode or "map"
    if area == "japan" and mode == "map":
        await _prefecture_map(ctx, scores, area, mode, _prefectures.load())


async def _prefecture_map(ctx: commands.Context, scores: ScoreStore, area: str, mode: str, regions: list) -> None:
    region = random.choice(regions)
    name = region["name"][0]
    try:
        data = await net.get_bytes(region["map_url"])
        file = await asyncio.to_thread(lambda: image_to_file(decode_image(data), "map.png"))
    except (net.FetchError, ImageDecodeError, OSError) as e:
        log.warning("Couldn't load map for %s: %s", name, e)
        await ctx.send("Something broke! Please try the command again")
        return

    embed = discord.Embed(title=f"You have {MAP_ROUND_SECONDS} seconds to guess the prefecture based on the map!",
                          colour=discord.Color.gold())
    embed.set_image(url="attachment://map.png")
    await ctx.send(embed=embed, file=file)

    def check(m: discord.Message) -> bool:
        return m.channel == ctx.channel and m.content.lower() == name.lower()

    try:
        msg = await ctx.bot.wait_for("message", check=check, timeout=MAP_ROUND_SECONDS)
    except asyncio.TimeoutError:
        await ctx.send(f"Sorry, nobody got the prefecture correct! The correct answer was: {name}")
        return
    await ctx.send(f"Good job {msg.author.mention}! The prefecture was {name}")
    scores.record_geography(msg.author, area, mode)


# --- geoguesser ----------------------------------------------------------------------------

def geoguesser_points(km: float) -> float:
    """Empirical fit of GeoGuessr's score (max ~5000) as a sum of gaussians over distance in km."""
    a = [4817.435, 914, 760, 160, 210, 37, -41.81, 43]
    b = [-49, 1400, 3040, 2380, 6600, 2800, 63, 8500]
    c = [670, 620, 1740, 600, 1000, 530, 364, 767]
    d = [-0.5, -0.5, -0.5, -0.5, -0.3, -0.5, -0.5, -0.5]
    return float(sum(ai * np.e ** (di * ((km - bi) / ci) ** 2) for ai, bi, ci, di in zip(a, b, c, d)))


def result_title(points: int) -> str:
    if points == 5000:
        options = ["Phenomenal job", "This is so poggers", "Unbelievable", "Very cool very swag", "Incredible",
                   "Congratulations"]
    elif points > 3000:
        options = ["Great job", "Excellent work", "Nice", "Super"]
    elif points > 1000:
        options = ["Good effort", "Alright", "Perfectly adequate", "Satisfactory", "Not too bad", "Cool"]
    elif points > 100:
        options = ["Nice try", "Better luck next time", "Good attempt", "Not quite there"]
    elif points > 0:
        options = ["Ouch", "Yikes", "Not great", "Unlucky", "Unfortunate"]
    else:
        options = ["Abysmal", "Wow that's horrible", "Horrible job", "Really off the mark on this one",
                   "You couldn't have done any worse if you tried"]
    return random.choice(options)


def parse_game_time(arg: str | None) -> int:
    if arg is not None and arg.isnumeric():
        return max(GEOGUESSER_MIN_SECONDS, min(GEOGUESSER_MAX_SECONDS, int(arg)))
    return GEOGUESSER_DEFAULT_SECONDS


def with_zoom(map_url: str, zoom: str) -> str:
    return re.sub(r"zoom=\d+", "zoom=" + zoom, map_url, count=1)


class Geocode:
    def __init__(self, lat: float, lng: float, map_url: str) -> None:
        self.lat, self.lng, self.map_url = lat, lng, map_url


async def geocode(query: str, key: str) -> Geocode | None:
    def lookup():
        return geocoder.mapquest(query, key=key)

    try:
        result = await asyncio.to_thread(lookup)
        map_url = (result.json or {}).get("raw", {}).get("mapUrl")
    except Exception:
        log.exception("Geocoding %r failed", query)
        return None
    if result.lat is None or result.lng is None or not map_url:
        return None
    return Geocode(result.lat, result.lng, map_url)


def _stitch_maps(images: list[bytes]) -> Image.Image:
    maps = [decode_image(data) for data in images]
    out = Image.new("RGB", (sum(m.width for m in maps) + 2 * (len(maps) - 1), maps[0].height), "black")
    x = 0
    for m in maps:
        out.paste(m, (x, 0))
        x += m.width + 2
    return out


async def three_zoom_map(map_url: str, filename: str) -> discord.File:
    """Street, regional and world zoom levels of the same map, side by side."""
    images = await asyncio.gather(*(net.get_bytes(with_zoom(map_url, zoom)) for zoom in MAP_ZOOMS))
    return await asyncio.to_thread(lambda: image_to_file(_stitch_maps(list(images)), filename))


async def _location_image(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.hostname in BUNDLED_IMAGE_HOSTS:
        bundled = ASSETS_DIR / "misc" / Path(parsed.path).name
        if bundled.is_file():
            return await asyncio.to_thread(bundled.read_bytes)
    return await net.get_bytes(url)


async def geoguesser_game(ctx: commands.Context, scores: ScoreStore, key: str | None,
                          time_arg: str | None = None) -> None:
    location = random.choice(_locations.load())
    game_time = parse_game_time(time_arg)
    colour = discord.Color.from_rgb(*(random.randint(0, 255) for _ in range(3)))

    try:
        data = await _location_image(location["url"])
        intro_file = await asyncio.to_thread(lambda: image_to_file(decode_image(data), "location.png"))
    except (net.FetchError, ImageDecodeError, OSError) as e:
        log.warning("Couldn't load geoguesser location %s: %s", location["url"], e)
        await ctx.send("Something broke! Please try the command again")
        return
    intro = discord.Embed(title=f"Here's your location! You have {game_time} seconds to guess the latitude, "
                                f"longitude pair, or enter a city/country!", colour=colour)
    intro.set_footer(text="NOTE: your next message will count as your answer!")
    intro.set_image(url="attachment://location.png")
    await ctx.send(embed=intro, file=intro_file)

    def check(m: discord.Message) -> bool:
        return m.author == ctx.author and m.channel == ctx.channel

    guess: Geocode | None = None
    guesser: discord.abc.User | None = None
    start = time.time()
    while True:
        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=game_time - (time.time() - start))
        except asyncio.TimeoutError:
            await ctx.send("Time's up!")
            break
        if msg.content.lower() in CONFIRM_WORDS and guess is not None:
            break
        result = await geocode(msg.clean_content, key or "")
        if result is None:
            await ctx.send("Sorry, something went wrong! Please try again")
            continue
        guess, guesser = result, msg.author

        remaining = game_time - (time.time() - start)
        embed = discord.Embed(title="Type yes (or y) to confirm your guess, otherwise, keep on guessing! "
                                    "You have %.2f seconds (%.3f minutes) left" % (remaining, remaining / 60),
                              colour=colour)
        embed.set_footer(text=f"Current guess lat/long: {guess.lat}, {guess.lng}")
        try:
            file = await three_zoom_map(guess.map_url, "map_user_guess.png")
        except (net.FetchError, ImageDecodeError, OSError):
            await ctx.send(embed=embed)
            continue
        embed.set_image(url="attachment://map_user_guess.png")
        await ctx.send(embed=embed, file=file)

    if guess is None:
        return

    dist = distance.distance((location["lat"], location["long"]), (guess.lat, guess.lng))
    points = int(geoguesser_points(dist.km))
    final = discord.Embed(colour=colour)
    final.add_field(name="Points", value=f"{points}{' :star: ' if points == 5000 else ''}")
    final.add_field(name="Distance", value="%.3f km, (%.3f miles)" % (dist.km, dist.miles))
    final.set_footer(text=f"Correct Lat/long: {location['lat']}, {location['long']}")

    final_file = None
    answer = await geocode(f"{location['lat']}, {location['long']}", key or "")
    if answer is not None:
        try:
            final_file = await three_zoom_map(answer.map_url, "final_map.png")
            final.set_image(url="attachment://final_map.png")
        except (net.FetchError, ImageDecodeError, OSError):
            final_file = None
    await ctx.send(result_title(points) + f" {guesser.mention}!")
    if final_file is not None:
        await ctx.send(embed=final, file=final_file)
    else:
        await ctx.send(embed=final)

    scores.record_geoguesser(guesser, points, dist.km)
