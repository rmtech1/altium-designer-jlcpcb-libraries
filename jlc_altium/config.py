"""Loads config.toml (or config.local.toml) and resolves its paths."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    raw: dict
    base: Path

    def section(self, name: str) -> dict:
        return self.raw.get(name, {})

    def path(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else (self.base / p)

    @property
    def output_dir(self) -> Path:
        return self.path(self.section("output").get("dir", "library"))

    @property
    def database_path(self) -> Path:
        return self.output_dir / self.section("output").get("database", "JLCPCB.sqlite")

    @property
    def dblib_path(self) -> Path:
        return self.output_dir / self.section("output").get("dblib", "JLCPCB.DbLib")

    @property
    def overrides_path(self) -> Path:
        return self.path(self.section("output").get("overrides", "overrides/parts.csv"))

    @property
    def cache_dir(self) -> Path:
        return self.base / ".cache"


def load(path: str | Path | None = None) -> Config:
    if path is None:
        local = REPO_ROOT / "config.local.toml"
        path = local if local.exists() else REPO_ROOT / "config.toml"
    path = Path(path).resolve()
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return Config(raw=raw, base=path.parent)
