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
    def opacity(self) -> float:
        return self._opacity

    def show_latest(self) -> RadarFrame:
        """Discover the newest frame and make it the visible radar overlay."""
        frame = self._provider.get_frames()[-1]
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
