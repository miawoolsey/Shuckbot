import asyncio
from modules.viewer import ViewerRegistry
from tests.fakes import FakeChannel, message


def test_navigation_flow():
    channel = FakeChannel()
    registry = ViewerRegistry()

    async def scenario():
        await registry.create(message(";img x", channel=channel, author_id=7), ["a", "b", "c"], "T")
        viewer = registry.current(channel.id)
        assert viewer.embed.footer.text == "Page 1 of 3"

        nav = message("b", channel=channel, author_id=7)
        await registry.handle_navigation(nav)
        assert viewer.page == 3  # wraps backwards
        assert nav.deleted
        await registry.handle_navigation(message("n", channel=channel, author_id=7))
        assert viewer.page == 1
        await registry.handle_navigation(message("p2", channel=channel, author_id=7))
        assert viewer.page == 2 and viewer.embed.image.url == "b"
        await registry.handle_navigation(message("p9", channel=channel, author_id=7))
        assert viewer.page == 2
        await registry.handle_navigation(message("n", channel=channel, author_id=8))  # not the searcher
        assert viewer.page == 2
        await registry.handle_navigation(message("please", channel=channel, author_id=7))
        assert viewer.page == 2

        await registry.handle_navigation(message("s", channel=channel, author_id=7))
        assert viewer.message.deleted
        assert registry.current(channel.id) is None

    asyncio.run(scenario())
