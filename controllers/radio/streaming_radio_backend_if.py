# SPDX-License-Identifier: MIT

"""Backend capabilities consumed by streaming-browser orchestration."""

from typing import Protocol
from ui.radio.streaming_radio_state_source_if import StreamingRadioStateSourceIf
from ui.radio.streaming_radio_types import StreamingRadioStation


class StreamingRadioBackendIf(StreamingRadioStateSourceIf, Protocol):
    """Serialize playback in the backend and expose immutable snapshots."""

    def play(self, station: StreamingRadioStation) -> None:
        """! @brief Start station playback.

        @param station Station metadata with resolved stream URL.
        """
        ...

    def stop(self) -> None:
        """! @brief Stop current streaming playback."""
        ...


class StreamingRadioFavoritesIf(Protocol):
    """Storage capabilities needed by browser workers."""

    @property
    def ordered_station_ids(self) -> tuple[str, ...]:
        """! @brief Read ordered persisted favorite identifiers.

        @return Favorite identifiers in user order.
        """
        ...

    @property
    def station_ids(self) -> frozenset[str]:
        """! @brief Read persisted favorite membership.

        @return Immutable favorite identifier set.
        """
        ...

    def toggle(self, station_id: str) -> bool:
        """! @brief Persist one membership change atomically.

        @param station_id Identifier whose membership should change.
        @return Whether the station is now a favorite.
        """
        ...
