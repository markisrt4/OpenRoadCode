# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.radio.streaming_radio_types import StreamingRadioStation


class StreamingRadioDirectoryIf(ABC):
    """Directory abstraction for discovering internet-radio stations."""

    @abstractmethod
    def search(self, query: str, *, limit: int = 20) -> tuple[StreamingRadioStation, ...]:
        """Find stations whose names match a user query.

        @param query User-entered station search text.
        @param limit Maximum number of stations to return.
        @return Matching stations in provider-defined relevance order.
        """

    @abstractmethod
    def stations_by_ids(
        self,
        station_ids: tuple[str, ...],
    ) -> tuple[StreamingRadioStation, ...]:
        """Resolve stable directory identifiers to current station metadata.

        @param station_ids Stable directory identifiers to resolve.
        @return Resolved stations in the requested identifier order when available.
        """

    @abstractmethod
    def stations_by_region(
        self,
        *,
        state: str,
        country_code: str = "US",
        limit: int = 50,
    ) -> tuple[StreamingRadioStation, ...]:
        """Return healthy stations for a state or regional label.

        @param state State, province, or regional label to search.
        @param country_code ISO-style country code used to constrain discovery.
        @param limit Maximum number of stations to return.
        @return Healthy stations matching the requested region.
        """

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
        """Return stations near a position, with regional fallback for missing geo metadata.

        @param latitude Geographic latitude in decimal degrees.
        @param longitude Geographic longitude in decimal degrees.
        @param radius_km Search radius in kilometers.
        @param state State, province, or regional fallback label.
        @param country_code ISO-style country code used to constrain discovery.
        @param limit Maximum number of stations to return.
        @return Stations near the requested position or matching the regional fallback.
        """
