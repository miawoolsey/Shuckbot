import asyncio

import pytest

from modules import net


@pytest.mark.parametrize("host,public", [
    ("8.8.8.8", True), ("2606:4700::1111", True),
    ("127.0.0.1", False), ("10.0.0.92", False), ("192.168.1.1", False), ("169.254.169.254", False),
    ("::1", False), ("fd00::1", False), ("0.0.0.0", False), ("not-an-ip", False),
])
def test_is_public_address(host, public):
    assert net.is_public_address(host) is public


@pytest.mark.parametrize("url", ["http://127.0.0.1:9/a.png", "http://10.0.0.92:3000/x.png", "http://localhost/a.png"])
def test_private_targets_are_refused(url):
    async def scenario():
        await net.start()
        try:
            with pytest.raises(net.FetchError):
                await net.get_bytes(url)
            assert await net.is_reachable(url) is False
        finally:
            await net.close()

    asyncio.run(scenario())
