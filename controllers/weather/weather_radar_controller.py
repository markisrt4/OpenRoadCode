# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-independent weather-radar orchestration."""

from __future__ import annotations

from controllers.weather.radar_palette import RadarPalette
from controllers.weather.radar_provider_if import RadarFrame, RadarProviderIf
from controllers.weather.radar_tile_service import RadarTileService


class WeatherRadarController:
    """Select radar frames and publish persistent overlay state to the map."""

    def __init__(self, provider: RadarProviderIf, map_renderer, *, opacity: float = 0.65,
                 palette: RadarPalette = RadarPalette.UNIVERSAL,
                 tile_service: RadarTileService | None = None) -> None:
        if not 0.0 <= opacity <= 1.0:
            raise ValueError("radar opacity must be between 0.0 and 1.0")
        self._provider = provider
        self._map_renderer = map_renderer
        self._opacity = opacity
        self._enabled = False
        self._palette = palette
        self._tile_service = tile_service
        self._frame: RadarFrame | None = None
        self._frames: tuple[RadarFrame, ...] = ()
        self._frame_index: int | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def frame_time(self) -> int | None:
        return self._frame.timestamp if self._frame is not None else None

    @property
    def palette(self) -> RadarPalette:
        return self._palette

    @property
    def has_frames(self) -> bool:
        """Return whether historical frames are available without a network request."""
        return bool(self._frames)

    @property
    def frame_times(self) -> tuple[int, ...]:
        """Return available timeline timestamps, oldest to newest."""
        return tuple(frame.timestamp for frame in self._frames)

    @property
    def frame_index(self) -> int | None:
        """Return the currently displayed timeline index."""
        return self._frame_index

    def select_frame(self, index: int) -> RadarFrame:
        """Select a cached timeline frame without a network request."""
        if not 0 <= index < len(self._frames):
            raise IndexError("radar frame index is outside the available history")
        return self._select_frame(index)

    @property
    def opacity(self) -> float:
        return self._opacity

    @property
    def is_live(self) -> bool:
        """Return whether the selected frame is the newest available frame."""
        return bool(self._frames) and self._frame_index == len(self._frames) - 1

    def set_provider(self, provider: RadarProviderIf) -> None:
        """Switch radar source and discard frame-selection state."""
        if provider is self._provider:
            return
        self._provider = provider
        self._frames = ()
        self._frame_index = None
        self._frame = None

    def show_latest(self) -> RadarFrame:
        """Discover available frames and make the newest one visible."""
        return self.show_frames(self.load_frames())

    def load_frames(self) -> tuple[RadarFrame, ...]:
        """Fetch frames without mutating presentation or touching the map socket."""
        frames = tuple(self._provider.get_frames())
        if not frames:
            raise RuntimeError("radar provider returned no frames")
        return frames

    def show_frames(self, frames: tuple[RadarFrame, ...]) -> RadarFrame:
        """Present previously fetched frames on the renderer-owning UI thread."""
        if not frames:
            raise ValueError("radar frames must not be empty")
        self._frames = frames
        return self._select_frame(len(self._frames) - 1)

    def previous_frame(self) -> RadarFrame:
        """Select the preceding cached historical frame."""
        if not self._frames or self._frame_index is None:
            return self.show_latest()
        return self._select_frame(max(0, self._frame_index - 1))

    def next_frame(self) -> RadarFrame:
        """Select the next cached frame, stopping at the live edge."""
        if not self._frames or self._frame_index is None:
            return self.show_latest()
        return self._select_frame(min(len(self._frames) - 1, self._frame_index + 1))

    def _select_frame(self, index: int) -> RadarFrame:
        frame = self._frames[index]
        self._frame_index = index
        self._frame = frame
        self._enabled = True
        self._publish_frame(frame)
        return frame

    def hide(self) -> None:
        """Hide radar without discarding the renderer's source/tile cache."""
        self._enabled = False
        self._map_renderer.set_weather_radar(None, enabled=False, opacity=self._opacity)

    def set_palette(self, palette: RadarPalette) -> None:
        """Change radar presentation without discovering or downloading a new frame."""
        self._palette = RadarPalette(palette)
        if self._enabled and self._frame is not None:
            self._publish_frame(self._frame)

    def set_opacity(self, opacity: float) -> None:
        if not 0.0 <= opacity <= 1.0:
            raise ValueError("radar opacity must be between 0.0 and 1.0")
        self._opacity = opacity
        if self._enabled:
            self._map_renderer.set_weather_radar(None, enabled=True, opacity=opacity)

    def refresh_renderer_state(self) -> None:
        """Replay radar state after the transient native renderer starts."""
        if self._enabled and self._frame is not None:
            self._publish_frame(self._frame)

    def _publish_frame(self, frame: RadarFrame) -> None:
        tile_url = (
            self._tile_service.tile_url(frame, self._palette)
            if self._tile_service is not None
            else frame.tile_url
        )
        self._map_renderer.set_weather_radar(
            tile_url,
            enabled=True,
            frame_time=frame.timestamp,
            opacity=self._opacity,
            max_zoom=frame.max_zoom,
        )
