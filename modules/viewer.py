"""Paginated image viewer embeds, navigated by typing n / b / p<number> / s in the channel."""
from __future__ import annotations

from dataclasses import dataclass, field

import discord

from modules.discord_utils import safe_delete


@dataclass
class Viewer:
    message: discord.Message
    embed: discord.Embed
    images: list[str]
    author_id: int
    authors: list[int] = field(default_factory=list)
    page: int = 1

    @property
    def length(self) -> int:
        return len(self.images)

    @property
    def current_image(self) -> str:
        return self.images[self.page - 1]


def _describe_author(guild: discord.Guild | None, user_id: int) -> str:
    member = guild.get_member(user_id) if guild else None
    return "By `" + str(member) + "`"


class ViewerRegistry:
    """At most one active viewer per channel; a new search replaces the previous one."""

    def __init__(self) -> None:
        self._by_channel: dict[int, Viewer] = {}

    async def create(self, message: discord.Message, images: list[str], title: str,
                     authors: list[int] | None = None) -> None:
        authors = list(authors or [])
        embed = discord.Embed(title=title)
        embed.set_image(url=images[0]).set_footer(text="Page 1 of " + str(len(images))) \
            .set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        if authors:
            embed.description = _describe_author(message.guild, authors[0])
        sent = await message.channel.send(embed=embed)
        self._by_channel[message.channel.id] = Viewer(sent, embed, images, message.author.id, authors)

    def current(self, channel_id: int) -> Viewer | None:
        return self._by_channel.get(channel_id)

    def _owned_viewer(self, message: discord.Message) -> Viewer | None:
        viewer = self._by_channel.get(message.channel.id)
        if viewer is None or viewer.author_id != message.author.id:
            return None
        return viewer

    async def handle_navigation(self, message: discord.Message) -> None:
        text = message.clean_content.lower()
        if text in ("b", "n"):
            viewer = self._owned_viewer(message)
            if viewer:
                if text == "b":
                    viewer.page = viewer.page - 1 if viewer.page > 1 else viewer.length
                else:
                    viewer.page = viewer.page + 1 if viewer.page < viewer.length else 1
                await self._show_page(viewer, message)
        elif text.startswith("p"):
            try:
                page = int(text[1:])
            except ValueError:
                return
            viewer = self._owned_viewer(message)
            if viewer and 1 <= page <= viewer.length:
                viewer.page = page
                await self._show_page(viewer, message)
        elif text == "s":
            viewer = self._owned_viewer(message)
            if viewer:
                self._by_channel.pop(message.channel.id, None)
                await safe_delete(viewer.message)
                await safe_delete(message)

    async def _show_page(self, viewer: Viewer, trigger: discord.Message) -> None:
        viewer.embed.set_image(url=viewer.current_image) \
            .set_footer(text="Page " + str(viewer.page) + " of " + str(viewer.length))
        if viewer.authors:
            viewer.embed.description = _describe_author(trigger.guild, viewer.authors[viewer.page - 1])
        try:
            await viewer.message.edit(embed=viewer.embed)
        except discord.NotFound:
            # Someone deleted the viewer; forget it so we stop trying to edit it.
            if self._by_channel.get(trigger.channel.id) is viewer:
                del self._by_channel[trigger.channel.id]
            return
        await safe_delete(trigger)


viewers = ViewerRegistry()
