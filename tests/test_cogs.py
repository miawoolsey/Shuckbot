"""Drive the real command callbacks with fake contexts (no Discord connection needed)."""
import asyncio
import io
import json
from types import SimpleNamespace

import pytest
from PIL import Image

from modules import core, image_input, imagefun, picturebook, tags
from modules.config import Config
from modules.games import Games
from modules.games import flags as flag_game
from modules.viewer import viewers
from tests.fakes import FakeChannel, message

CONFIG = Config(token="t", owner_id=999)


class FakeUser:
    def __init__(self, user_id):
        self.id, self.name = user_id, f"name{user_id}"

    def __str__(self):
        return self.name


class FakeBot:
    def __init__(self, replies=()):
        self._replies = list(replies)

    def get_user(self, user_id):
        return FakeUser(user_id)

    async def fetch_user(self, user_id):
        return self.get_user(user_id)

    async def wait_for(self, event, check=None, timeout=None):
        for reply in self._replies:
            if check(reply):
                self._replies.remove(reply)
                return reply
        raise asyncio.TimeoutError


class Ctx:
    def __init__(self, msg, bot=None, guild_id=42, admin=False):
        self.message, self.channel, self.bot = msg, msg.channel, bot or FakeBot()
        self.guild = SimpleNamespace(id=guild_id, get_member=lambda user_id: None) if guild_id else None
        msg.guild = self.guild
        msg.author.guild_permissions = SimpleNamespace(administrator=admin, manage_messages=admin, manage_guild=admin)
        self.author = msg.author

    async def send(self, content=None, **kwargs):
        return await self.channel.send(content, **kwargs)


def run(coro):
    return asyncio.run(coro)


def ctx_for(text, channel=None, author_id=1, **kwargs):
    channel = channel or FakeChannel()
    msg = message(text, channel=channel, author_id=author_id)
    channel._history.insert(0, msg)  # like Discord, history includes the command message itself
    return Ctx(msg, **kwargs)


# --- tags --------------------------------------------------------------------------------------

@pytest.fixture
def tag_cog(tmp_path, monkeypatch):
    monkeypatch.setattr(tags, "BASE_DIR", tmp_path)
    return tags.Tags(FakeBot(), CONFIG)


def tag_cmd(cog, text, **kwargs):
    ctx = ctx_for(text, **kwargs)
    run(cog.tag.callback(cog, ctx))
    return ctx.channel.texts, ctx.channel.sent


def test_tag_lifecycle(tag_cog, tmp_path):
    assert tag_cmd(tag_cog, ";t add Bees According to all known laws")[0] == ["Added tag **Bees**!"]
    assert tag_cmd(tag_cog, ";t add bees again")[0] == ["Tag **bees** already exists!"]
    assert tag_cmd(tag_cog, ";t BEES")[0] == ["According to all known laws"]
    assert tag_cmd(tag_cog, ";t edit bees hacked", author_id=2)[0] == ["You are not the author of tag **bees**!"]
    assert tag_cmd(tag_cog, ";t edit bees")[0] == ["Syntax error\n`;tag edit <tag> <content>`"]
    assert tag_cmd(tag_cog, ";t edit bees new content")[0] == ["Edited tag **bees**!"]
    assert tag_cmd(tag_cog, ";t owner bees")[0] == ["Tag **bees** is owned by `name1`"]
    assert tag_cmd(tag_cog, ";t owner nope")[0] == ["Tag **nope** does not exist"]
    assert tag_cmd(tag_cog, ";t remove bees", author_id=999)[0] == ["Removed tag **bees**!"]  # bot owner
    assert tag_cmd(tag_cog, ";t bees")[0] == ["Tag **bees** not found!"]
    assert tag_cmd(tag_cog, ";t")[0][0].startswith("Syntax error")
    on_disk = json.loads((tmp_path / "tags.json").read_text())
    assert on_disk == {"_default": {}}


def test_tag_disable_enable(tag_cog):
    tag_cmd(tag_cog, ";t add hi hello")
    assert tag_cmd(tag_cog, ";t disable hi")[0][0].startswith("Sorry bud")
    assert tag_cmd(tag_cog, ";t disable hi", admin=True)[0] == ["Tag **hi** has been disabled in the server!"]
    assert tag_cmd(tag_cog, ";t hi")[0] == ["Tag **hi** has been disabled in this server!"]
    assert tag_cmd(tag_cog, ";t hi", guild_id=None)[0] == ["hello"]  # DMs aren't a server
    assert tag_cmd(tag_cog, ";t enable hi", admin=True)[0] == ["Tag **hi** has been enabled!"]
    # "all" works even though no tag is literally named "all"
    assert tag_cmd(tag_cog, ";t disable all", admin=True)[0][0].startswith("Tags have been disabled serverwide")
    assert tag_cmd(tag_cog, ";t hi")[0] == [tags.MSG_ALL_DISABLED]
    assert tag_cmd(tag_cog, ";t enable ALL", admin=True)[0] == ["Tags have been re-enabled!"]
    assert tag_cmd(tag_cog, ";t hi")[0] == ["hello"]


def test_tag_list_with_many_tags(tag_cog):
    for i in range(150):
        tag_cog.tags.insert({"tag": f"some-long-tag-name-{i}", "content": "x", "owner": 1})
    _, sent = tag_cmd(tag_cog, ";t list")
    embed = sent[0].kwargs["embed"]
    assert all(len(f.value) <= 1024 for f in embed.fields) and len(embed.fields) > 1
    assert tag_cmd(tag_cog, ";t list", author_id=5)[0] == ["You don't own any tags!"]


# --- prefixes ----------------------------------------------------------------------------------

def test_prefix_command_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "BASE_DIR", tmp_path)
    store = core.PrefixStore()
    cog = core.Core(FakeBot(), CONFIG, store)
    ctx = ctx_for(";prefix !")
    run(cog.prefix.callback(cog, ctx, "!"))
    assert ctx.channel.texts == ["You need the **Manage Server** permission to do that."]
    for args, reply in [(("ab",), "**Format**: ;prefix <single character>"), ((), "**Format**: ;prefix <single character>"),
                        (("é",), "You must choose an ASCII character!"), (("!",), 'Set server prefix to "!".')]:
        ctx = ctx_for(";prefix", admin=True)
        run(cog.prefix.callback(cog, ctx, *args))
        assert ctx.channel.texts == [reply]
    assert core.PrefixStore().get(42) == "!"
    assert store.get(None) == ";" and store.get(7) == ";"


# --- image commands ----------------------------------------------------------------------------

def _png_bytes(size=(64, 48), colour="red"):
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def fake_net(monkeypatch):
    async def get_bytes(url, **kwargs):
        if "missing" in url:
            raise image_input.net.FetchError("404", status=404)
        return _png_bytes()
    monkeypatch.setattr(image_input.net, "get_bytes", get_bytes)
    monkeypatch.setattr(imagefun.net, "get_bytes", get_bytes)


@pytest.mark.parametrize("command", ["holding", "exm", "fantano", "kim", "twice", "draw", "heejin", "school",
                                     "lecture", "tesla", "osu", "mokou", "megumin", "weezer", "sickos",
                                     "tomscott", "one", "rgb", "purple", "mix", "sort", "shift", "shuffle"])
def test_image_commands_post_a_file_and_clean_up(fake_net, command):
    cog = imagefun.ImageFun(FakeBot())
    ctx = ctx_for(f";{command} https://x.com/pic.png 3")
    run(getattr(cog, command).callback(cog, ctx))
    files = [s for s in ctx.channel.sent if "file" in s.kwargs]
    assert len(files) == 1
    progress = [s for s in ctx.channel.sent if s.content and s.content.startswith("Processing")]
    assert progress and all(p.deleted for p in progress)


def test_image_command_with_dead_url(fake_net):
    cog = imagefun.ImageFun(FakeBot())
    ctx = ctx_for(";holding https://x.com/missing.png")
    run(cog.holding.callback(cog, ctx))
    assert image_input.MSG_INVALID_IMAGE in ctx.channel.texts
    assert all(s.deleted for s in ctx.channel.sent if s.content.startswith("Processing"))


@pytest.mark.parametrize("command,text,reply", [
    ("resize", ";resize https://x.com/a.png", "Hey you need to add a number to the end of the command!"),
    ("resize", ";resize https://x.com/a.png nan", "Hey you need to add a number to the end of the command!"),
    ("shift", ";shift https://x.com/a.png 5 sideways",
     "Hey! Those are not valid arguments! It should either look like ;shift <number> <argument>  or  ;shift <number> !"),
    ("noise", ";noise 5", "Hey! You need to enter two values with your command for height and width!"),
    ("noise", ";noise 5 x", "Hey! You didnt enter valid numbers for height and width!"),
    ("color", ";color", "Hey you need to add a hex code or rgb values to the end of the command!"),
    ("color", ";color zzzzzz", "Hey you need to add a valid hex code to the end of the command!"),
])
def test_image_command_argument_errors(fake_net, command, text, reply):
    cog = imagefun.ImageFun(FakeBot())
    ctx = ctx_for(text)
    run(getattr(cog, command).callback(cog, ctx))
    assert ctx.channel.texts == [reply]


def test_resize_clamps_and_size(fake_net):
    cog = imagefun.ImageFun(FakeBot())
    ctx = ctx_for(";resize https://x.com/a.png 500")
    run(cog.resize.callback(cog, ctx))
    assert "Changing the resize factor to **10**" in ctx.channel.texts
    ctx = ctx_for(";size https://x.com/a.png")
    run(cog.size.callback(cog, ctx))
    assert ctx.channel.texts == ["The images dimensions are: (64, 48) !"]


def test_noise_resizes_and_shuffle_reports_factor(fake_net):
    cog = imagefun.ImageFun(FakeBot())
    ctx = ctx_for(";noise 900 0")
    run(cog.noise.callback(cog, ctx))
    assert ctx.channel.sent[0].edits[-1]["content"] == "Resizing to (500, 1), Processing."
    ctx = ctx_for(";shuffle https://x.com/a.png 2")
    run(cog.shuffle.callback(cog, ctx))
    assert "Shuffled the image by **2.0** !" in ctx.channel.texts


def test_undo_finds_image_before_bot_output(fake_net):
    history = [
        message("", bot=True, attachments=[SimpleNamespace(url="https://cdn/result.png")]),
        message(";holding https://x.com/original.png"),
    ]
    channel = FakeChannel(history)
    cog = imagefun.ImageFun(FakeBot())
    ctx = ctx_for(";undo", channel=channel)
    run(cog.undo.callback(cog, ctx))
    assert [s.kwargs["file"].filename for s in channel.sent if "file" in s.kwargs] == ["undo.png"]

    ctx = ctx_for(";undo", channel=FakeChannel([message("hi")]))
    run(cog.undo.callback(cog, ctx))
    assert ctx.channel.texts[-1] == "There's nothing to undo!"


# --- picturebook -------------------------------------------------------------------------------

def test_picturebook_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(picturebook, "BASE_DIR", tmp_path)

    async def reachable(url):
        return True
    monkeypatch.setattr(image_input.net, "is_reachable", reachable)
    cog = picturebook.Picturebook(FakeBot(), CONFIG)
    channel = FakeChannel(channel_id=77)

    def pb(text, *args, author_id=1):
        ctx = ctx_for(text, channel=channel, author_id=author_id)
        run(cog.pb.callback(cog, ctx, *args))
        return ctx.channel.texts[-1] if ctx.channel.texts else None

    assert pb(";pb") == "There are no saved images in this server! Use `;save` to save one."
    assert pb(";pb add https://x.com/1.png", "add", "https://x.com/1.png") == "Image saved!"
    assert pb(";pb add https://x.com/1.png", "add", "https://x.com/1.png") == "That image is already in the picturebook!"
    pb(";pb add https://x.com/2.png", "add", "https://x.com/2.png", author_id=2)
    pb(";pb")
    assert viewers.current(77).images == ["https://x.com/2.png", "https://x.com/1.png"]  # newest first
    assert pb(";pb rm", "rm") == "You are not the creator of the current image!"
    assert pb(";pb rm", "rm", author_id=999) == "Removed the current image!"  # bot owner can remove


# --- games -------------------------------------------------------------------------------------

def test_game_without_arguments_lists_games(tmp_path):
    cog = Games(FakeBot(), CONFIG)
    ctx = ctx_for(";game")
    run(cog.game.callback(cog, ctx))
    assert ctx.channel.texts == ["**The list of available games are:**\n\t*;game colour* - guess the hexcode!"]


def test_flag_game_round(tmp_path, monkeypatch):
    async def get_bytes(url, **kwargs):
        return _png_bytes()
    monkeypatch.setattr(flag_game.net, "get_bytes", get_bytes)
    monkeypatch.setattr(flag_game, "pick_flag", lambda difficulty: {"name": ["Laos", "Lao"], "url": "u"})
    channel = FakeChannel()
    winner = message("lao", channel=channel, author_id=5)
    winner.author.mention = "<@5>"
    cog = Games(FakeBot([message("wrong", channel=channel), winner]), CONFIG)
    cog.scores = flag_game.ScoreStore(tmp_path / "scores.json")
    ctx = ctx_for(";game flag hard", channel=channel)
    ctx.bot = cog.bot
    run(cog.game.callback(cog, ctx))
    assert channel.sent[0].kwargs["embed"].title == "You have 15 seconds to guess the country!"
    assert channel.texts[-1] == "Good job <@5>! The country was Laos"
    assert json.loads((tmp_path / "scores.json").read_text())["<@5>"]["flag"]["difficulty_3"] == 1
