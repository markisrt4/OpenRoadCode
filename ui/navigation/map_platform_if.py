"""Toolkit-independent selection and state for alternative map platforms."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class MapPlatform(str, Enum):
    MAPLIBRE = "MapLibre"
    EARTH = "Google Earth"


@dataclass(frozen=True, slots=True)
class MapPlatformState:
    active: MapPlatform = MapPlatform.MAPLIBRE
    requested: MapPlatform = MapPlatform.MAPLIBRE
    busy: bool = False
    status: str = "MapLibre"


class MapPlatformControlIf(Protocol):
    """Select a map platform without exposing browser or process access."""

    @property
    def state(self) -> MapPlatformState:
        """Return an immutable presentation snapshot.

        @return Current map state.
        """
        ...

    def request_platform(self, platform: MapPlatform) -> None:
        """Request another map platform.

        @param platform Desired map platform.
        """
        ...

    def request_chase(self) -> None:
        """Select Earth's close oblique follow view."""
        ...

    def resize(self, width: int, height: int, owner_window_id: int) -> None:
        """Update native host geometry.

        @param width Host width in pixels.
        @param height Host height in pixels.
        @param owner_window_id Persistent shell window for detaching a warm client.
        """
        ...

    def close(self) -> None:
        """Cancel map work and release owned resources."""
        ...
