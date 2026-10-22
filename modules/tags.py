"""Global text tags that anyone can create, with per-server disabling."""
from __future__ import annotations

import random

import discord
from discord.ext import commands
from tinydb import Query

from modules.config import BASE_DIR, Config
from modules.discord_utils import is_nsfw
from modules.storage import open_db

Tag = Query()
Disabled = Query()

FIELD_VALUE_LIMIT = 1024
MAX_EMBED_FIELDS = 25
# Names with special meaning for `tag disable/enable` rather than referring to a tag.
DISABLE_ALL = "all"
DISABLE_RANDOM = "random"

MSG_ALL_DISABLED = ("Tags have been disabled in this server! An admin can re-enable them with"
                    " the command `;t enable all`")


def _can_moderate(author: discord.abc.User) -> bool:
    perms = getattr(author, "guild_permissions", None)
    return perms is not None and (perms.administrator or perms.manage_messages)


def _numbered_list_fields(names: list[str]) -> list[str]:
    """Split "1. tag\\n2. tag..." into chunks that fit in embed fields."""
    fields, current = [], ""
    for i, name in enumerate(names, start=1):
        line = f"{i}. {name}"[:FIELD_VALUE_LIMIT - 1] + "\n"
        if len(current) + len(line) > FIELD_VALUE_LIMIT:
            fields.append(current)
            current = ""
        current += line
    if current:
        fields.append(current)
    return fields[:MAX_EMBED_FIELDS]


class Tags(commands.Cog):
    def __init__(self, bot: commands.Bot, config: Config) -> None:
        self.bot = bot
        self.config = config
        self.tags = open_db(BASE_DIR / "tags.json")
        self.disabled = open_db(BASE_DIR / "tags_disabled.json")
        self.all_disabled = open_db(BASE_DIR / "tags_servers_disabled.json")

    def _find(self, name: str) -> dict | None:
        return self.tags.get(Tag.tag == name.lower())

    def _may_edit(self, tag: dict, user_id: int) -> bool:
        return tag["owner"] == user_id or self.config.is_owner(user_id)

    def _is_disabled(self, guild_id: int, name: str) -> bool:
        return self.disabled.contains((Disabled.tag_name == name) & (Disabled.server_number == guild_id))

    def _all_disabled(self, guild_id: int) -> bool:
        return self.all_disabled.contains(Disabled.server_number == guild_id)

    @commands.command(aliases=["t"])
    async def tag(self, ctx: commands.Context) -> None:
        args = ctx.message.clean_content.split(" ", 3)
        if len(args) < 2:
            await self.syntax_error(ctx)
            return
        handler = {
            "add": self.add,
            "remove": self.remove,
            "delete": self.remove,
            "edit": self.edit,
            "owner": self.owner,
            "list": self.owned,
            "random": self.get_random,
            "disable": self.disable,
            "enable": self.enable,
        }.get(args[1], self.get)
        await handler(ctx, args)

    async def syntax_error(self, ctx: commands.Context) -> None:
        await ctx.send("Syntax error\n```fix\ntag <tag>\ntag add <tag> <content>"
                       "\ntag edit <tag> <content>\ntag remove <tag>\ntag owner <tag>```")

    async def add(self, ctx: commands.Context, args: list[str]) -> None:
        if len(args) < 4:
            await ctx.send("Syntax error\n`;tag add <tag> <content>`")
        elif self._find(args[2]):
            await ctx.send("Tag **" + args[2] + "** already exists!")
        else:
            self.tags.insert({"tag": args[2].lower(), "content": args[3], "owner": ctx.author.id})
            await ctx.send("Added tag **" + args[2] + "**!")

    async def remove(self, ctx: commands.Context, args: list[str]) -> None:
        if len(args) < 3:
            await ctx.send("Syntax error\n`;tag remove <tag> (<content>)`")
            return
        tag = self._find(args[2])
        if tag is None:
            await ctx.send("Tag **" + args[2] + "** not found!")
        elif self._may_edit(tag, ctx.author.id):
            self.tags.remove(Tag.tag == args[2].lower())
            await ctx.send("Removed tag **" + args[2] + "**!")
        else:
            await ctx.send("You are not the author of tag **" + args[2] + "**!")

    async def edit(self, ctx: commands.Context, args: list[str]) -> None:
        if len(args) < 3:
            await ctx.send("Syntax error\n`;tag edit <tag> (<content>)`")
            return
        tag = self._find(args[2])
        if tag is None:
            await ctx.send("Tag **" + args[2] + "** not found!")
        elif not self._may_edit(tag, ctx.author.id):
            await ctx.send("You are not the author of tag **" + args[2] + "**!")
        elif len(args) < 4:
            await ctx.send("Syntax error\n`;tag edit <tag> <content>`")
        else:
            self.tags.update({"content": args[3]}, Tag.tag == args[2].lower())
            await ctx.send("Edited tag **" + args[2] + "**!")

    async def owner(self, ctx: commands.Context, args: list[str]) -> None:
        if len(args) < 3:
            await self.syntax_error(ctx)
            return
        tag = self._find(args[2])
        if tag is None:
            await ctx.send("Tag **" + args[2] + "** does not exist")
            return
        tag_owner = self.bot.get_user(tag["owner"]) or await self.bot.fetch_user(tag["owner"])
        await ctx.send("Tag **" + args[2] + "** is owned by `" + str(tag_owner) + "`")

    async def owned(self, ctx: commands.Context, args: list[str]) -> None:
        mentions = ctx.message.mentions
        target_id = mentions[0].id if mentions else ctx.author.id
        results = self.tags.search(Tag.owner == target_id)
        if not results and not mentions:
            await ctx.send("You don't own any tags!")
        elif not results:
            await ctx.send(mentions[0].display_name + " doesn't own any tags!")
        else:
            embed = discord.Embed(title="Tag list", colour=discord.Color.gold())
            for value in _numbered_list_fields([tag["tag"] for tag in results]):
                embed.add_field(name="Tags", value=value, inline=False)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

    async def get(self, ctx: commands.Context, args: list[str]) -> None:
        name = args[1]
        tag = self._find(name)
        if tag is None:
            await ctx.send(f"Tag **{name}** not found!")
            return
        if ctx.guild is not None:
            if self._is_disabled(ctx.guild.id, name.lower()):
                await ctx.send(f"Tag **{name}** has been disabled in this server!")
                return
            if self._all_disabled(ctx.guild.id):
                await ctx.send(MSG_ALL_DISABLED)
                return
        await ctx.send(tag["content"])

    async def get_random(self, ctx: commands.Context, args: list[str]) -> None:
        if not is_nsfw(ctx.channel):
            await ctx.send("Sorry, you can only use this command in nsfw channels!")
            return
        if ctx.guild is not None:
            if self._is_disabled(ctx.guild.id, DISABLE_RANDOM):
                await ctx.send("The random tag has been disabled in this server! An admin can re enable this "
                               "feature with `;t enable random`")
                return
            if self._all_disabled(ctx.guild.id):
                await ctx.send(MSG_ALL_DISABLED)
                return
        all_tags = self.tags.all()
        if all_tags:
            await ctx.send(random.choice(all_tags)["content"])

    async def disable(self, ctx: commands.Context, args: list[str]) -> None:
        if len(args) < 3:
            await ctx.send("You need to add a tag to disable! If you wish to disable all tags, please write"
                           " `;t disable all`")
            return
        if ctx.guild is None or not _can_moderate(ctx.author):
            await ctx.send("Sorry bud, you don't have the manage message permission! "
                           "You can't disable tags in the server")
            return
        tag_name = args[2].lower()
        if tag_name not in (DISABLE_ALL, DISABLE_RANDOM) and self._find(tag_name) is None:
            await ctx.send(f"Tag **{args[2]}** not found!")
            return
        guild_id = ctx.guild.id
        if tag_name == DISABLE_ALL:
            if self._all_disabled(guild_id):
                await ctx.send("Tags are already disabled, you can reenable tags with the command "
                               "`;t enable all`!")
            else:
                self.all_disabled.insert({"server_number": guild_id})
                await ctx.send("Tags have been disabled serverwide, you can reenable tags with the "
                               "command `;t enable all`!")
            return
        if self._is_disabled(guild_id, tag_name):
            await ctx.send(f"Tag **{tag_name}** is already disabled!")
            return
        self.disabled.insert({"tag_name": tag_name, "server_number": guild_id, "disabled_by": ctx.author.id})
        await ctx.send(f"Tag **{tag_name}** has been disabled in the server!")

    async def enable(self, ctx: commands.Context, args: list[str]) -> None:
        if len(args) < 3:
            await ctx.send("You need to add a tag to enable! If you wish to re-enable tags server-wide use "
                           "the `;t enable all` command!")
            return
        if ctx.guild is None or not _can_moderate(ctx.author):
            await ctx.send("Sorry bud, you don't have the manage message permission! "
                           "You can't enable tags in the server")
            return
        tag_name = args[2]
        lowered = tag_name.lower()
        if lowered not in (DISABLE_ALL, DISABLE_RANDOM) and self._find(lowered) is None:
            await ctx.send(f"Tag **{tag_name}** not found!")
            return
        guild_id = ctx.guild.id
        if lowered == DISABLE_ALL:
            if self._all_disabled(guild_id):
                self.all_disabled.remove(Disabled.server_number == guild_id)
                await ctx.send("Tags have been re-enabled!")
            else:
                await ctx.send("Tags are already enabled!")
            return
        if self._is_disabled(guild_id, lowered):
            self.disabled.remove((Disabled.tag_name == lowered) & (Disabled.server_number == guild_id))
            await ctx.send(f"Tag **{tag_name}** has been enabled!")
        else:
            await ctx.send(f"Tag **{tag_name}** is already enabled!")
