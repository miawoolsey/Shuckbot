"""A server-wide collection of saved images."""
from __future__ import annotations

from discord.ext import commands
from tinydb import Query

from modules.config import BASE_DIR, Config
from modules.image_input import URL_SOURCE, find_image_url
from modules.storage import open_db
from modules.viewer import viewers

Image = Query()


class Picturebook(commands.Cog):
    def __init__(self, bot: commands.Bot, config: Config) -> None:
        self.bot = bot
        self.config = config
        self.db = open_db(BASE_DIR / "picturebook.json")

    def _table(self, guild_id: int):
        return self.db.table(str(guild_id))

    @commands.command(aliases=["picturebook", "photobook"])
    @commands.guild_only()
    async def pb(self, ctx: commands.Context, *args: str) -> None:
        if not args:
            await self.show(ctx)
        elif args[0] in ("add", "save"):
            await self.save(ctx)
        elif args[0] in ("remove", "delete", "rm"):
            await self.remove(ctx)

    async def save(self, ctx: commands.Context) -> None:
        image = await find_image_url(ctx.message, URL_SOURCE)
        if image is None:
            return
        table = self._table(ctx.guild.id)
        if table.contains(Image.image == image):
            await ctx.send("That image is already in the picturebook!")
            return
        table.insert({"server": ctx.guild.id, "image": image, "owner": ctx.author.id})
        await ctx.send("Image saved!")

    async def show(self, ctx: commands.Context) -> None:
        saved = self._table(ctx.guild.id).all()
        if not saved:
            await ctx.send("There are no saved images in this server! Use `;save` to save one.")
            return
        newest_first = list(reversed(saved))
        await viewers.create(ctx.message, [item["image"] for item in newest_first], "Picturebook",
                             authors=[item["owner"] for item in newest_first])

    async def remove(self, ctx: commands.Context) -> None:
        current = viewers.current(ctx.channel.id)
        if current is None:
            await ctx.send("You don't have an image selected in the picturebook!")
            return
        table = self._table(ctx.guild.id)
        result = table.get(Image.image == current.current_image)
        if result is None:
            await ctx.send("Something has gone terribly wrong! Sorry!")
        elif result["owner"] == ctx.author.id or self.config.is_owner(ctx.author.id):
            table.remove(Image.image == current.current_image)
            await ctx.send("Removed the current image!")
        else:
            await ctx.send("You are not the creator of the current image!")
