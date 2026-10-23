"""Finding the image a user wants a command to work on.

Sources, in priority order:
  * an image URL right after the command
  * the avatar of a mentioned user
  * an image attached to the command message
  * the most recent image in the last 20 messages (attachment, embed, or URL in text)
"""
from __future__ import annotations

import asyncio
import io
import re
from contextlib import aclosing
from dataclasses import dataclass
from typing import AsyncIterator

import discord
from PIL import Image, UnidentifiedImageError

from modules import net
from modules.discord_utils import avatar_url

IMAGE_EXTENSIONS = re.compile(r"\.(png|jpe?g|gif|webp)", re.IGNORECASE)
STATIC_IMAGE_EXTENSIONS = re.compile(r"\.(png|jpe?g|webp)", re.IGNORECASE)

HISTORY_LIMIT = 20
# Compressed downloads are capped in net.py; this caps the decoded size (a tiny PNG can decode
# to gigabytes). 50M pixels is e.g. 8660x5770.
MAX_IMAGE_PIXELS = 50_000_000
# CPU-heavy image work runs in threads; bound how many run at once so a burst of commands
# can't exhaust memory.
MAX_CONCURRENT_IMAGE_JOBS = 3
_image_jobs = asyncio.Semaphore(MAX_CONCURRENT_IMAGE_JOBS)

MSG_URL_FORMAT = ("Your URL is not properly formatted! Currently I can only process URL's "
                  "that end in .png, .jpg, .gif, or .webp")
MSG_STATIC_URL_FORMAT = ("Your URL is not properly formatted! Currently I can only process URL's "
                         "that end in .png, .jpg, or .webp")
MSG_NOT_FOUND = "Your URL is not properly formatted or I couldn't find an image!"
MSG_BAD_ATTACHMENT = "Your attached image is not a valid file type! (png, jpg, gif)"
MSG_INVALID_IMAGE = "Your image is invalid!"
MSG_BROKEN_IMAGE = "There's something wrong with your image :("

_EXPLICIT, _DIRECT, _HISTORY = "explicit", "direct", "history"


class ImageInputError(Exception):
    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class ImageDecodeError(Exception):
    pass


@dataclass(frozen=True)
class ImageSource:
    pattern: re.Pattern
    allow_mentions: bool
    # Mentioned users' server avatar (image edits) vs. their global avatar (picturebook).
    server_avatar: bool
    # Stop searching history at the newest message with media, even if it's an unsupported type.
    stop_at_unsupported: bool
    not_found_with_args: str
    not_found_without_args: str


EDIT_SOURCE = ImageSource(IMAGE_EXTENSIONS, True, True, False, MSG_URL_FORMAT, MSG_NOT_FOUND)
URL_SOURCE = ImageSource(IMAGE_EXTENSIONS, True, False, False, MSG_URL_FORMAT, MSG_URL_FORMAT)
VISION_SOURCE = ImageSource(STATIC_IMAGE_EXTENSIONS, False, False, True, MSG_STATIC_URL_FORMAT,
                            MSG_STATIC_URL_FORMAT)


def looks_like_image_url(word: str, pattern: re.Pattern = IMAGE_EXTENSIONS) -> bool:
    return word.startswith("http") and pattern.search(word) is not None


def _media_urls(message: discord.Message) -> list[str]:
    urls = []
    if message.attachments:
        urls.append(message.attachments[0].url)
    if message.embeds and message.embeds[0].image and message.embeds[0].image.url:
        urls.append(message.embeds[0].image.url)
    return urls


def message_image_urls(message: discord.Message, pattern: re.Pattern = IMAGE_EXTENSIONS) -> list[str]:
    urls = [url for url in _media_urls(message) if pattern.search(url)]
    urls += [word for word in message.clean_content.split(" ") if looks_like_image_url(word, pattern)]
    return urls


async def history_image_urls(channel, source: ImageSource, limit: int = HISTORY_LIMIT) -> AsyncIterator[str]:
    async for message in channel.history(limit=limit):
        for url in _media_urls(message):
            if source.pattern.search(url):
                yield url
            elif source.stop_at_unsupported:
                return
        for word in message.clean_content.split(" "):
            if looks_like_image_url(word, source.pattern):
                yield word


async def _candidates(message: discord.Message, source: ImageSource) -> AsyncIterator[tuple[str, str]]:
    args = message.clean_content.split(" ")
    if len(args) >= 2:
        if looks_like_image_url(args[1], source.pattern):
            yield _EXPLICIT, args[1]
            return
        if source.allow_mentions and message.mentions:
            user = message.mentions[0]
            yield _DIRECT, user.display_avatar.url if source.server_avatar else avatar_url(user)
            return
    elif message.attachments:
        url = message.attachments[0].url
        if not source.pattern.search(url):
            raise ImageInputError(MSG_BAD_ATTACHMENT)
        yield _DIRECT, url
        return
    async for url in history_image_urls(message.channel, source):
        yield _HISTORY, url


def _not_found(message: discord.Message, source: ImageSource) -> ImageInputError:
    has_args = len(message.clean_content.split(" ")) >= 2
    return ImageInputError(source.not_found_with_args if has_args else source.not_found_without_args)


def decode_image(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > MAX_IMAGE_PIXELS:
            raise ImageDecodeError(f"image is too large ({img.width}x{img.height})")
        img.load()
        return img
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as e:
        raise ImageDecodeError(str(e)) from e


async def run_image_job(func, *args):
    """Run CPU-heavy image work in a worker thread, with bounded concurrency."""
    async with _image_jobs:
        return await asyncio.to_thread(func, *args)


async def download_image(url: str) -> Image.Image:
    data = await net.get_bytes(url)
    return await run_image_job(decode_image, data)


async def read_image(message: discord.Message, source: ImageSource = EDIT_SOURCE) -> Image.Image | None:
    """Download and decode the image the user meant. Tells the user and returns None on failure."""
    try:
        async with aclosing(_candidates(message, source)) as candidates:
            async for kind, url in candidates:
                try:
                    return await download_image(url)
                except (net.FetchError, ImageDecodeError):
                    if kind == _HISTORY:
                        continue  # a dead link in chat history: keep looking further back
                    raise ImageInputError(MSG_INVALID_IMAGE if kind == _EXPLICIT else MSG_BROKEN_IMAGE)
        raise _not_found(message, source)
    except ImageInputError as e:
        await message.channel.send(e.user_message)
        return None


async def find_image_url(message: discord.Message, source: ImageSource = URL_SOURCE) -> str | None:
    """Like :func:`read_image` but only returns the URL (for storing or passing to another API)."""
    try:
        async with aclosing(_candidates(message, source)) as candidates:
            async for kind, url in candidates:
                if kind == _EXPLICIT and not await net.is_reachable(url):
                    raise ImageInputError(MSG_INVALID_IMAGE)
                return url
        raise _not_found(message, source)
    except ImageInputError as e:
        await message.channel.send(e.user_message)
        return None
