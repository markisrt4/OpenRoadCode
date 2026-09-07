# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.radio.streaming_radio_types import StreamingRadioStation


class StreamingRadioDirectoryIf(ABC):
    """Directory abstraction for discovering internet-radio stations."""

    @abstractmethod
    def search(self, query: str, *, limit: int = 20) -> tuple[StreamingRadioStation, ...]:
        """Find stations whose names match a user query."""

    @abstractmethod
    def stations_by_region(
        self,
        *,
        state: str,
        country_code: str = "US",
        limit: int = 50,
    ) -> tuple[StreamingRadioStation, ...]:
        """Return healthy stations for a state or regional label."""

    @abstractmethod
    def stations_near(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_km: float,
        state: str,
        country_code: str = "US",
        limit: int = 50,
    ) -> tuple[StreamingRadioStation, ...]:
        """Return stations near a position, with regional fallback for missing geo metadata."""
