import asyncio

import pytest

import Shuckbot as entrypoint
from modules import core, picturebook, tags
from modules.config import Config

# Every command and alias the original Shuckbot.py registered.
ORIGINAL_COMMANDS = {
    "prefix": {"shuckbotprefix", "shuckprefix"}, "ping": set(), "page": {"help"}, "img": {"i", "im", "image"},
    "r34": set(), "invite": set(), "pb": {"picturebook", "photobook"}, "tag": {"t"}, "metar": set(), "taf": set(),
    "holding": {"hold"}, "exm": {"exmilitary"}, "fantano": {"fan", "review", "tnd"}, "one": {"1bit", "1"},
    "kim": set(), "emote": {"e"}, "sort": {"pixelsort", "sortpixels"}, "shuffle": {"pixelshuffle"},
    "resize": {"scale"}, "size": set(), "twice": {"mina"}, "draw": {"drawing"}, "undo": set(),
    "heejin": {"loona"}, "school": set(), "lecture": {"lect"}, "tesla": set(), "osu": set(),
    "color": {"colour", "c"}, "mix": {"noisy"}, "noise": set(), "mokou": {"gf"}, "shift": set(),
    "megumin": {"megu"}, "weezer": set(), "game": {"g"}, "rgb": {"torgb", "2rgb"}, "avatar": {"a"},
    "purple": set(), "whatifitwaspurple": set(), "tomscott": {"tom"}, "sickos": set(), "readycheck": set(),
    "id": {"identify"}, "landmark": {"landmarks"},
}


@pytest.fixture
def bot(tmp_path, monkeypatch):
    for module in (core, tags, picturebook):
        monkeypatch.setattr(module, "BASE_DIR", tmp_path)

    async def build():
        instance = entrypoint.Shuckbot(Config(token="x"))
        await instance.setup_hook()
        return instance

    loop = asyncio.new_event_loop()
    instance = loop.run_until_complete(build())
    yield instance
    loop.run_until_complete(entrypoint.net.close())
    loop.close()


def test_all_original_commands_and_aliases_registered(bot):
    registered = {command.name: set(command.aliases) for command in bot.commands}
    assert registered == ORIGINAL_COMMANDS


def test_game_cooldown_kept(bot):
    cooldown = bot.get_command("game")._buckets._cooldown
    assert (cooldown.rate, cooldown.per) == (1, 5)


def test_readycheck_view_is_persistent(bot):
    assert any(view.is_persistent() for view in bot.persistent_views)
