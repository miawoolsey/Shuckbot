"""Bot configuration and filesystem locations.

Secrets are read from ``keys.txt`` (``key=value`` per line, see ``keys.txt.template``).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODULES_DIR = BASE_DIR / "modules"
ASSETS_DIR = BASE_DIR / "assets"

DEFAULT_PREFIX = ";"


def _parse_keys_file(path: Path) -> dict[str, str]:
    params: dict[str, str] = {}
    with path.open(encoding="utf-8") as file:
        for line in file:
            key, sep, value = line.partition("=")
            if sep:
                params[key.strip()] = value.strip()
    return params


@dataclass(frozen=True)
class Config:
    token: str
    owner_id: int | None = None
    google_key: str | None = None
    avwx_key: str | None = None
    invite_url: str | None = None
    mapquest_key: str | None = None
    google_json: Path | None = None

    @classmethod
    def load(cls, path: Path = BASE_DIR / "keys.txt") -> "Config":
        params = _parse_keys_file(path)
        owner = params.get("ownerID")
        google_json = params.get("googleJson")
        return cls(
            token=params["token"],
            owner_id=int(owner) if owner and owner.isdigit() else None,
            google_key=params.get("googleKey"),
            avwx_key=params.get("avwxKey"),
            invite_url=params.get("url"),
            mapquest_key=params.get("mapquest"),
            google_json=(BASE_DIR / google_json) if google_json else None,
        )

    def is_owner(self, user_id: int) -> bool:
        return self.owner_id is not None and user_id == self.owner_id
