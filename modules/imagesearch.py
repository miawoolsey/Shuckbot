"""Google image search and rule34 search, shown in a paginated viewer."""
from __future__ import annotations

import logging
import random
import xml.etree.ElementTree as ElementTree
from urllib.parse import quote

import discord
from discord.ext import commands

from modules import net
from modules.discord_utils import is_nsfw
from modules.viewer import viewers

log = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
GOOGLE_SEARCH_ENGINE_ID = "017178301722928584583:yi4kptiqtbq"
R34_URL = "https://rule34.xxx/index.php?page=dapi&s=post&q=index&limit=1000&tags="

MSG_QUOTA = "The daily quota for Google searches has been exceeded."
MSG_CONNECTION = "Connection error. Please try again."
MSG_NO_RESULTS = "No results found!"


class ImageSearch(commands.Cog):
    def __init__(self, bot: commands.Bot, google_key: str | None) -> None:
        self.bot = bot
        self.google_key = google_key

    @commands.command(aliases=["i", "im", "image"])
    async def img(self, ctx: commands.Context) -> None:
        parts = ctx.message.clean_content.split(" ", 1)
        if len(parts) < 2:
            return
        query = parts[1]
        params = {"key": self.google_key or "", "cx": GOOGLE_SEARCH_ENGINE_ID, "q": query, "searchType": "image"}
        try:
            status, result = await net.get_json(GOOGLE_SEARCH_URL, params=params)
        except net.FetchError as e:
            log.warning("Google search failed: %s", e)
            await ctx.send(MSG_CONNECTION)
            return
        if status != 200:  # Google answers 403/429 once the daily quota is used up
            log.warning("Google search returned HTTP %s: %s", status, result)
            await ctx.send(MSG_QUOTA)
            return
        images = [item["link"] for item in result.get("items", []) if "link" in item]
        if not images:
            await ctx.send(MSG_NO_RESULTS)
            return
        await viewers.create(ctx.message, images, "Google search for " + query)

    @commands.command()
    async def r34(self, ctx: commands.Context) -> None:
        if not is_nsfw(ctx.channel):
            await ctx.send("Hey! This isn't an nsfw channel! You can't use that here!")
            return
        parts = ctx.message.clean_content.split(" ", 1)
        if len(parts) < 2:
            return
        tags = parts[1]
        try:
            body = await net.get_bytes(R34_URL + quote(tags))
            posts = ElementTree.fromstring(body)
        except (net.FetchError, ElementTree.ParseError) as e:
            log.warning("r34 search for %r failed: %s", tags, e)
            return
        images = [post.get("file_url") for post in posts if post.get("file_url")]
        if not images:
            await ctx.send(MSG_NO_RESULTS)
            return
        random.shuffle(images)
        await viewers.create(ctx.message, images, "r34 search for " + tags)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.author.bot:
            await viewers.handle_navigation(message)
