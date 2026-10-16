"""Toolkit-independent selection and state for alternative map platforms."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class MapPlatform(str, Enum):
    MAPLIBRE = "MapLibre"
    CESIUM = "3D map"
    EARTH = "Google Earth"


class ExplorationCameraAction(str, Enum):
    """Renderer-neutral, relative camera actions for destination exploration."""

    PAN_UP = 'pan-up'
    PAN_DOWN = 'pan-down'
    PAN_LEFT = 'pan-left'
    PAN_RIGHT = 'pan-right'
    ZOOM_IN = 'zoom-in'
    ZOOM_OUT = 'zoom-out'
    PITCH_UP = 'pitch-up'
    PITCH_DOWN = 'pitch-down'
    NORTH = 'north'
    RECENTER = 'recenter'
    DIMENSION = 'dimension'


@dataclass(frozen=True, slots=True)
class MapPlatformState:
    active: MapPlatform = MapPlatform.MAPLIBRE
    requested: MapPlatform = MapPlatform.MAPLIBRE
    busy: bool = False
    status: str = "MapLibre"
    available_platforms: tuple[MapPlatform, ...] = (MapPlatform.MAPLIBRE, MapPlatform.EARTH)
    follow_enabled: bool = False
    position_available: bool = False


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

    def request_camera(self, action: ExplorationCameraAction) -> None:
        """Apply a relative camera action to the active exploration surface."""
        ...

    def request_follow(self, enabled: bool) -> None:
        """Enable vehicle following on the exploration surface; await a live fix if needed."""
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
