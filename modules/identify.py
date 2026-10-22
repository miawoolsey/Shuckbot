"""Google Cloud Vision powered image labelling and landmark detection."""
from __future__ import annotations

import asyncio
import logging
from functools import cached_property

from discord.ext import commands
from PIL import Image, ImageDraw

from modules.config import Config
from modules.discord_utils import Progress, image_to_file
from modules.image_input import VISION_SOURCE, ImageDecodeError, download_image, find_image_url
from modules.net import FetchError

log = logging.getLogger(__name__)

MSG_BAD_IMAGE = "I don't like that image! Try another one 🙂"
BOX_COLOUR = "#00ff00"


def describe_labels(descriptions: list[str]) -> str:
    """e.g. "I can see cat, whiskers, and fur." """
    items = [d.lower() for d in descriptions]
    if len(items) == 1:
        return f"I can see {items[0]}."
    if len(items) > 1:
        return "I can see " + ", ".join(items[:-1]) + ", and " + items[-1] + "."
    return "I can see ."


def draw_landmarks(img: Image.Image, landmarks) -> Image.Image:
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)
    for item in landmarks:
        vx = item.bounding_poly.vertices
        draw.rectangle([vx[0].x, vx[0].y, vx[2].x, vx[3].y], outline=BOX_COLOUR, width=3)
        draw.text([vx[0].x, vx[0].y - 10], item.description, fill=BOX_COLOUR, stroke_fill="black", stroke_width=3)
    return img


class Identify(commands.Cog):
    def __init__(self, bot: commands.Bot, config: Config) -> None:
        self.bot = bot
        self.config = config

    @cached_property
    def _client(self):
        from google.cloud import vision
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(str(self.config.google_json))
        return vision.ImageAnnotatorClient(credentials=creds)

    def _annotate(self, method: str, url: str):
        from google.cloud import vision

        image = vision.Image()
        image.source.image_uri = url
        return getattr(self._client, method)(image=image)

    @commands.command(aliases=["identify"])
    async def id(self, ctx: commands.Context) -> None:
        async with Progress(ctx.channel, "Processing...") as progress:
            url = await find_image_url(ctx.message, VISION_SOURCE)
            if url is None:
                return
            try:
                response = await asyncio.to_thread(self._annotate, "label_detection", url)
            except Exception:
                log.exception("Vision label detection failed")
                return
            if response.error.message:
                await progress.resolve(MSG_BAD_IMAGE)
            else:
                await progress.resolve(describe_labels([label.description for label in response.label_annotations]))

    @commands.command(aliases=["landmarks"])
    async def landmark(self, ctx: commands.Context) -> None:
        async with Progress(ctx.channel, "Processing...") as progress:
            url = await find_image_url(ctx.message, VISION_SOURCE)
            if url is None:
                return
            try:
                response = await asyncio.to_thread(self._annotate, "landmark_detection", url)
            except Exception:
                log.exception("Vision landmark detection failed")
                return
            if response.error.message:
                log.info("Vision error: %s", response.error.message)
                await progress.resolve(MSG_BAD_IMAGE)
                return
            landmarks = list(response.landmark_annotations)
            if not landmarks:
                await progress.resolve("I don't know this place!")
                return
            answer = "I think it's " + landmarks[0].description + "."
            try:
                img = await download_image(url)
            except (FetchError, ImageDecodeError):
                await progress.resolve(answer)
                return
            file = await asyncio.to_thread(lambda: image_to_file(draw_landmarks(img, landmarks), "landmark.png"))
            await progress.finish()
            await ctx.send(content=answer, file=file)
