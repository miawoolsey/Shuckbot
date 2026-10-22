import pytest

from modules import help as help_module
from modules.discord_utils import split_message
from modules.identify import describe_labels
from modules.readycheck import parse_state, render, toggle
from modules.tags import _numbered_list_fields


def test_help_pages():
    embed, icon = help_module.build_help("", 0)
    assert embed.title == "Shuckbot help" and icon is not None
    assert embed.footer.icon_url == "attachment://shuck.png"
    assert help_module.build_help("3", 0)[0].title == "Image editor commands [N - Z]"
    assert help_module.build_help("99", 0)[0].title == "Game commands"
    assert help_module.build_help("game", 0)[0].title == "Game commands"
    assert help_module.build_help("nonsense", 0)[0].title == "Shuckbot help"


def test_help_for_command():
    embed, icon = help_module.build_help("img", 0)
    assert icon is None
    assert embed.title == "Image command help!"
    assert embed.fields[0].name == "Description:"
    assert help_module.build_help("g f", 0)[0].title == "Game flag command help!"


def test_help_icons_exist():
    for name in help_module.SHUCK_ICONS:
        assert (help_module.ASSETS_DIR / "help" / name).is_file()


def test_split_message():
    text = "".join(f"line {i}\n" for i in range(600))
    chunks = split_message(text)
    assert "".join(chunks) == text
    assert all(len(c) <= 2000 for c in chunks)
    assert split_message("x" * 4500) == ["x" * 2000, "x" * 2000, "x" * 500]


def test_tag_list_fields_fit_embed_limits():
    fields = _numbered_list_fields([f"tag-number-{i}" for i in range(300)])
    assert all(len(f) <= 1024 for f in fields)
    assert fields[0].startswith("1. tag-number-0\n")
    assert len(fields) <= 25


def test_readycheck_roundtrip_and_toggle():
    content = render("<@&1>", {"bob", "al"}, {"cy"})
    assert content == "READY CHECK <@&1>\nREADY (2): al, bob\nNOT READY (1): cy"
    ready, not_ready = parse_state(content)
    assert (ready, not_ready) == ({"al", "bob"}, {"cy"})
    toggle("cy", ready, not_ready)
    assert "cy" in ready and "cy" not in not_ready
    toggle("cy", ready, not_ready)
    assert "cy" not in ready
    assert parse_state(render("<@&1>", set(), set())) == (set(), set())


@pytest.mark.parametrize("labels,text", [
    (["Cat"], "I can see cat."),
    (["Cat", "Fur"], "I can see cat, and fur."),
    (["Cat", "Fur", "Whiskers"], "I can see cat, fur, and whiskers."),
])
def test_describe_labels(labels, text):
    assert describe_labels(labels) == text
