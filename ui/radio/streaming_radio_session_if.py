# SPDX-License-Identifier: MIT

"""Semantic browser requests, presentation, and lifecycle contracts."""

from abc import ABC, abstractmethod
from typing import Protocol

from .streaming_radio_state import StreamingRadioBrowseMode, StreamingRadioBrowserState


class StreamingRadioRequestHandlerIf(ABC):
    """Handle browser intent without exposing directories, storage, or workers."""

    @abstractmethod
    def request_mode(self, mode: StreamingRadioBrowseMode) -> None:
        """! @brief Request stations for a browsing mode.

        @param mode Local, regional, or favorites browsing mode.
        """
        ...

    @abstractmethod
    def request_play(self, station_id: str) -> None:
        """! @brief Request playback of a displayed station.

        @param station_id Stable station identifier from display state.
        """
        ...

    @abstractmethod
    def request_stop(self) -> None:
        """! @brief Request that streaming playback stop."""
        ...

    @abstractmethod
    def request_toggle_favorite(self, station_id: str) -> None:
        """! @brief Toggle a displayed station's persisted favorite membership.

        @param station_id Stable station identifier from display state.
        """
        ...

    @abstractmethod
    def request_artwork(self, station_id: str) -> None:
        """! @brief Request display artwork for one station.

        @param station_id Stable station identifier from display state.
        """
        ...


class StreamingRadioUiIf(Protocol):
    """Render immutable browser state and encoded artwork on the frontend thread."""

    def set_streaming_request_handler(self, handler: StreamingRadioRequestHandlerIf | None) -> None:
        """! @brief Bind or retire semantic requests.

        @param handler Request handler or None to disconnect presentation.
        """
        ...

    def set_streaming_state(self, state: StreamingRadioBrowserState) -> None:
        """! @brief Replace the browser display state.

        @param state Immutable browser and playback snapshot.
        """
        ...

    def set_station_artwork(self, station_id: str, payload: bytes) -> None:
        """! @brief Deliver encoded artwork for frontend decoding and rendering.

        @param station_id Identifier of the station owning this artwork.
        @param payload Encoded image bytes; the frontend owns toolkit image objects.
        """
        ...


class StreamingRadioSessionIf(Protocol):
    """Lifecycle supplied by composition; hiding preserves shared playback."""

    def activate(self, view: StreamingRadioUiIf) -> None:
        """! @brief Bind a visible browser and load its browsing mode.

        @param view Browser presentation to bind.
        """
        ...

    def deactivate(self) -> None:
        """! @brief Retire presentation and invalidate pending deliveries."""
        ...

    def close(self) -> None:
        """! @brief Permanently retire this browser session."""
        ...
