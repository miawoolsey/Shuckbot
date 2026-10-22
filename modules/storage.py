"""Persistent JSON storage helpers.

All writes are atomic (write to a temp file, then rename) so a crash mid-write can never
leave a truncated/corrupt data file behind. Reads are served from memory, so the data
files are only parsed once instead of on every query.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from tinydb import TinyDB
from tinydb.storages import Storage


def atomic_write_json(path: Path, data: Any, **dump_kwargs: Any) -> None:
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(data, tmp, **dump_kwargs)
            tmp.flush()
            os.fsync(tmp.fileno())
        _copy_ownership(path, tmp_name)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _copy_ownership(original: Path, replacement: str) -> None:
    """Keep the original file's mode/owner so host users can still edit bind-mounted data."""
    try:
        st = os.stat(original)
    except FileNotFoundError:
        os.chmod(replacement, 0o664)
        return
    os.chmod(replacement, st.st_mode & 0o7777)
    try:
        os.chown(replacement, st.st_uid, st.st_gid)
    except (PermissionError, AttributeError):
        pass


def _read_json_file(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if text.strip() else None


class CachedJSONStorage(Storage):
    """TinyDB storage that keeps the database in memory and writes through atomically.

    The on-disk format is identical to TinyDB's default ``JSONStorage``.
    """

    def __init__(self, path: str | Path, **dump_kwargs: Any) -> None:
        self._path = Path(path)
        self._dump_kwargs = dump_kwargs
        self._cache: dict | None = None
        self._loaded = False
        if not self._path.exists():
            self._path.touch()

    def read(self) -> dict | None:
        if not self._loaded:
            self._cache = _read_json_file(self._path)
            self._loaded = True
        return self._cache

    def write(self, data: dict) -> None:
        atomic_write_json(self._path, data, **self._dump_kwargs)
        self._cache = data
        self._loaded = True

    def close(self) -> None:
        pass


def open_db(path: Path) -> TinyDB:
    return TinyDB(path, storage=CachedJSONStorage)


class JsonDocument:
    """A whole-file JSON document held in memory and written back atomically."""

    def __init__(self, path: Path, default: Callable[[], Any] = dict, **dump_kwargs: Any) -> None:
        self._path = Path(path)
        self._default = default
        self._dump_kwargs = dump_kwargs
        self._data: Any = None

    @property
    def data(self) -> Any:
        if self._data is None:
            loaded = _read_json_file(self._path) if self._path.exists() else None
            self._data = loaded if loaded is not None else self._default()
        return self._data

    def save(self) -> None:
        atomic_write_json(self._path, self.data, **self._dump_kwargs)


class ReloadingJsonFile:
    """Read-only JSON file cached in memory, re-read only when its mtime changes."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._mtime: float | None = None
        self._data: Any = None

    def load(self) -> Any:
        mtime = self._path.stat().st_mtime
        if mtime != self._mtime:
            with self._path.open(encoding="utf-8") as file:
                self._data = json.load(file)
            self._mtime = mtime
        return self._data
