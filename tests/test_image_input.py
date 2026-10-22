import asyncio

import pytest

from modules import image_input
from tests.fakes import FakeChannel, attachment, embed_with_image, message


def _collect(msg, source):
    async def run():
        return [item async for item in image_input._candidates(msg, source)]
    return asyncio.run(run())


def test_explicit_url_wins():
    msg = message(";holding https://x.com/a.PNG?size=2")
    assert _collect(msg, image_input.EDIT_SOURCE) == [("explicit", "https://x.com/a.PNG?size=2")]


def test_mention_avatar_used():
    from types import SimpleNamespace
    user = SimpleNamespace(avatar=None, default_avatar=SimpleNamespace(url="https://cdn/default.png"))
    msg = message(";holding @someone", mentions=[user])
    assert _collect(msg, image_input.EDIT_SOURCE) == [("direct", "https://cdn/default.png")]
    assert _collect(msg, image_input.VISION_SOURCE) == []  # vision doesn't use avatars


def test_bad_attachment_reports_error():
    msg = message(";holding", attachments=[attachment("https://cdn/file.txt")])
    with pytest.raises(image_input.ImageInputError) as e:
        _collect(msg, image_input.EDIT_SOURCE)
    assert e.value.user_message == image_input.MSG_BAD_ATTACHMENT


def test_history_search_order():
    history = [
        message("no images here"),
        message("look https://x.com/old.gif and https://x.com/b.jpg"),
        message("", attachments=[attachment("https://cdn/c.webp")], embeds=[embed_with_image("https://e/d.png")]),
    ]
    msg = message(";holding", channel=FakeChannel(history))
    assert [u for _, u in _collect(msg, image_input.EDIT_SOURCE)] == [
        "https://x.com/old.gif", "https://x.com/b.jpg", "https://cdn/c.webp", "https://e/d.png"]


def test_vision_stops_at_newest_unsupported_media():
    history = [message("", attachments=[attachment("https://cdn/anim.gif")]),
               message("", attachments=[attachment("https://cdn/ok.png")])]
    msg = message(";id", channel=FakeChannel(history))
    assert _collect(msg, image_input.VISION_SOURCE) == []


def test_read_image_skips_broken_history_links(monkeypatch):
    calls = []

    async def fake_download(url):
        calls.append(url)
        if "broken" in url:
            raise image_input.ImageDecodeError("nope")
        return "IMAGE"

    monkeypatch.setattr(image_input, "download_image", fake_download)
    history = [message("https://x.com/broken.png"), message("https://x.com/good.png")]
    msg = message(";kim", channel=FakeChannel(history))
    assert asyncio.run(image_input.read_image(msg)) == "IMAGE"
    assert calls == ["https://x.com/broken.png", "https://x.com/good.png"]


@pytest.mark.parametrize("text,expected", [
    (";kim", image_input.MSG_NOT_FOUND),
    (";kim notaurl", image_input.MSG_URL_FORMAT),
])
def test_read_image_not_found_messages(text, expected):
    msg = message(text)
    assert asyncio.run(image_input.read_image(msg)) is None
    assert msg.channel.texts == [expected]


def test_read_image_invalid_explicit_url(monkeypatch):
    async def fail(url):
        raise image_input.net.FetchError("down")

    monkeypatch.setattr(image_input, "download_image", fail)
    msg = message(";kim https://x.com/a.png")
    assert asyncio.run(image_input.read_image(msg)) is None
    assert msg.channel.texts == [image_input.MSG_INVALID_IMAGE]
