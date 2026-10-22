"""Shared non-blocking HTTP client.

The old code used ``requests`` inside coroutines, which froze the whole bot (including
the Discord heartbeat) for every download. Everything now goes through one shared
aiohttp session.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

USER_AGENT = "Shuckbot/2.0 (+https://github.com/miawoolsey/Shuckbot)"
DEFAULT_TIMEOUT = 15
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024


class FetchError(Exception):
    """Raised for any failed request: connection problems, timeouts, HTTP errors, oversize bodies."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


_session: aiohttp.ClientSession | None = None


async def start() -> None:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            headers={"User-Agent": USER_AGENT},
        )


async def close() -> None:
    global _session
    if _session is not None:
        await _session.close()
        _session = None


def session() -> aiohttp.ClientSession:
    if _session is None or _session.closed:
        raise RuntimeError("net.start() has not been called")
    return _session


async def get_bytes(url: str, *, params: dict | None = None, max_bytes: int = MAX_DOWNLOAD_BYTES) -> bytes:
    try:
        async with session().get(url, params=params) as resp:
            if resp.status >= 400:
                raise FetchError(f"HTTP {resp.status} for {url}", status=resp.status)
            if resp.content_length is not None and resp.content_length > max_bytes:
                raise FetchError(f"{url} is too large ({resp.content_length} bytes)")
            body = bytearray()
            async for chunk in resp.content.iter_chunked(64 * 1024):
                body += chunk
                if len(body) > max_bytes:
                    raise FetchError(f"{url} is larger than {max_bytes} bytes")
            return bytes(body)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        raise FetchError(f"Request to {url} failed: {e!r}") from e


async def get_json(url: str, *, params: dict | None = None) -> tuple[int, Any]:
    """Return ``(status, parsed_json)``. Raises FetchError on network failure or a non-JSON body."""
    try:
        async with session().get(url, params=params) as resp:
            text = await resp.text()
            return resp.status, json.loads(text)
    except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeDecodeError) as e:
        raise FetchError(f"Request to {url} failed: {e!r}") from e
    except json.JSONDecodeError as e:
        raise FetchError(f"{url} did not return JSON") from e


async def is_reachable(url: str) -> bool:
    try:
        async with session().get(url) as resp:
            return resp.status < 400
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return False
