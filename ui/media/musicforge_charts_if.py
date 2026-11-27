"""Toolkit-independent MusicForge charts contract."""

from __future__ import annotations

from typing import Protocol


class MusicForgeChartsIf(Protocol):
    """Read-only access to observed radio airplay rankings."""

    def stations(self) -> list[dict]:
        """List stations available as chart filters.

        @return Station records.
        """
        ...

    def songs(self, *, station: str | None = None, period: str = "today", limit: int = 20) -> dict:
        """Fetch the song chart for the requested station and period.

        @param station Optional station identifier.
        @param period Chart time window.
        @param limit Maximum number of ranked entries.
        @return Song chart response.
        """
        ...

    def artists(
        self, *, station: str | None = None, period: str = "today", limit: int = 20
    ) -> dict:
        """Fetch the artist chart for the requested station and period.

        @param station Optional station identifier.
        @param period Chart time window.
        @param limit Maximum number of ranked entries.
        @return Artist chart response.
        """
        ...
