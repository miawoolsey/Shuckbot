"""Minimal stand-ins for discord.py objects, enough to drive the cogs offline."""
from __future__ import annotations

import itertools
from types import SimpleNamespace

_ids = itertools.count(1000)


class FakeSent:
    def __init__(self, channel, content=None, **kwargs):
        self.id = next(_ids)
        self.channel = channel
        self.content = content
        self.kwargs = kwargs
        self.deleted = False
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        if "content" in kwargs:
            self.content = kwargs["content"]

    async def delete(self):
        self.deleted = True


class FakeChannel:
    def __init__(self, history=(), channel_id=1):
        self.id = channel_id
        self.sent: list[FakeSent] = []
        self._history = list(history)  # newest first

    async def send(self, content=None, **kwargs):
        sent = FakeSent(self, content, **kwargs)
        self.sent.append(sent)
        return sent

    async def history(self, limit=100):
        for message in self._history[:limit]:
            yield message

    @property
    def texts(self):
        return [s.content for s in self.sent if s.content]


class FakeMessage(SimpleNamespace):
    deleted = False

    async def delete(self):
        self.deleted = True


def attachment(url):
    return SimpleNamespace(url=url)


def embed_with_image(url):
    return SimpleNamespace(image=SimpleNamespace(url=url))


def message(text="", *, author_id=1, bot=False, attachments=(), embeds=(), mentions=(), channel=None):
    author = SimpleNamespace(id=author_id, bot=bot, display_name=f"user{author_id}",
                             display_avatar=SimpleNamespace(url="https://cdn/avatar.png"))
    return FakeMessage(id=next(_ids), content=text, clean_content=text, author=author,
                           attachments=list(attachments), embeds=list(embeds), mentions=list(mentions),
                           channel=channel or FakeChannel(), guild=None)
