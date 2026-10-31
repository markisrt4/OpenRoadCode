"""Toolkit-independent MusicForge charts contract."""
from __future__ import annotations

from typing import Protocol


class MusicForgeChartsIf(Protocol):
    """Read-only access to observed radio airplay rankings."""

    def stations(self) -> list[dict]: ...

    def songs(self, *, station: str | None = None, period: str = "today",
              limit: int = 20) -> dict: ...

    def artists(self, *, station: str | None = None, period: str = "today",
                limit: int = 20) -> dict: ...
