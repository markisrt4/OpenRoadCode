# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.weather import RadarFrame, RadarPalette, WeatherRadarController


class _Provider:
    provider_id = "test"

    def get_frames(self):
        return (
            RadarFrame(timestamp=100, tile_url="https://example.test/100/{z}/{x}/{y}.png"),
            RadarFrame(timestamp=200, tile_url="https://example.test/200/{z}/{x}/{y}.png", max_zoom=7),
        )


class _Renderer:
    def __init__(self):
        self.commands = []

    def set_weather_radar(self, tile_url, *, enabled=True, frame_time=None, opacity=0.65, max_zoom=22):
        self.commands.append((tile_url, enabled, frame_time, opacity, max_zoom))


def test_show_latest_publishes_newest_frame() -> None:
    renderer = _Renderer()
    controller = WeatherRadarController(_Provider(), renderer)

    frame = controller.show_latest()

    assert frame.timestamp == 200
    assert controller.enabled is True
    assert renderer.commands[-1] == (
        "https://example.test/200/{z}/{x}/{y}.png",
        True,
        200,
        0.65,
        7,
    )


def test_hide_preserves_frame_for_renderer_restart() -> None:
    renderer = _Renderer()
    controller = WeatherRadarController(_Provider(), renderer)
    controller.show_latest()

    controller.hide()
    controller.refresh_renderer_state()

    assert controller.enabled is False
    assert renderer.commands[-1] == (None, False, None, 0.65, 22)


def test_refresh_renderer_state_replays_visible_frame() -> None:
    renderer = _Renderer()
    controller = WeatherRadarController(_Provider(), renderer)
    controller.show_latest()
    renderer.commands.clear()

    controller.refresh_renderer_state()

    assert renderer.commands == [
        ("https://example.test/200/{z}/{x}/{y}.png", True, 200, 0.65, 7)
    ]


def test_opacity_update_does_not_refetch_frame() -> None:
    renderer = _Renderer()
    controller = WeatherRadarController(_Provider(), renderer)
    controller.show_latest()
    renderer.commands.clear()

    controller.set_opacity(0.4)

    assert renderer.commands == [(None, True, None, 0.4, 22)]


class _TileService:
    def tile_url(self, frame, palette):
        return f"http://127.0.0.1/radar/{frame.timestamp}/{palette.value}/{{z}}/{{x}}/{{y}}.png"


def test_palette_change_republishes_same_frame_through_tile_service() -> None:
    renderer = _Renderer()
    controller = WeatherRadarController(_Provider(), renderer, tile_service=_TileService())
    controller.show_latest()
    renderer.commands.clear()

    controller.set_palette(RadarPalette.CLASSIC)

    assert controller.palette is RadarPalette.CLASSIC
    assert renderer.commands == [
        (
            "http://127.0.0.1/radar/200/classic/{z}/{x}/{y}.png",
            True,
            200,
            0.65,
            7,
        )
    ]
