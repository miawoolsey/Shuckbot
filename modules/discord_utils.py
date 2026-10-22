"""Small helpers shared by the cogs."""
from __future__ import annotations

import io
import logging

import discord
from PIL import Image

log = logging.getLogger(__name__)

MESSAGE_LIMIT = 2000


def is_nsfw(channel: discord.abc.Messageable) -> bool:
    check = getattr(channel, "is_nsfw", None)
    return bool(check()) if callable(check) else False


def avatar_url(user: discord.abc.User) -> str:
    """The user's own avatar (not a per-server one), falling back to Discord's default avatar."""
    return (user.avatar or user.default_avatar).url


def image_to_file(img: Image.Image, filename: str, **save_kwargs) -> discord.File:
    """Encode a PIL image in memory. Blocking: call via ``asyncio.to_thread`` for big images."""
    buffer = io.BytesIO()
    img.save(buffer, format=save_kwargs.pop("format", None) or _format_for(filename), **save_kwargs)
    buffer.seek(0)
    return discord.File(buffer, filename=filename)


def bytes_to_file(data: bytes, filename: str) -> discord.File:
    return discord.File(io.BytesIO(data), filename=filename)


def _format_for(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {"jpg": "JPEG", "jpeg": "JPEG", "gif": "GIF", "webp": "WEBP"}.get(ext, "PNG")


def split_message(text: str, limit: int = MESSAGE_LIMIT) -> list[str]:
    """Split text into Discord-sized chunks, preferring line boundaries."""
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return chunks


async def send_long(channel: discord.abc.Messageable, text: str) -> None:
    for chunk in split_message(text):
        await channel.send(chunk)


async def safe_delete(message: discord.Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        pass


class Progress:
    """A temporary "Processing..." status message that is always cleaned up.

    The old code left "Processing ." messages behind forever whenever a command crashed.
    """

    def __init__(self, channel: discord.abc.Messageable, text: str) -> None:
        self._channel = channel
        self._text = text
        self.message: discord.Message | None = None

    async def __aenter__(self) -> "Progress":
        self.message = await self._channel.send(self._text)
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.finish()

    async def update(self, text: str) -> None:
        if self.message is None:
            return
        try:
            await self.message.edit(content=text)
        except discord.NotFound:
            self.message = None

    async def resolve(self, text: str) -> None:
        """Turn the status message into the final answer, so it is kept instead of deleted."""
        await self.update(text)
        self.message = None

    async def finish(self) -> None:
        message, self.message = self.message, None
        await safe_delete(message)
