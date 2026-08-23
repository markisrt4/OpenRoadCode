# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from concurrent.futures import Future
import time

from controllers.lighting.lighting_types import RgbColor
from controllers.music_lighting.music_lighting_output import MusicLightingOutput
from controllers.music_lighting.music_lighting_output_adapter import MusicLightingOutputAdapter


def _done() -> Future[None]:
    future: Future[None] = Future()
    future.set_result(None)
    return future


class _FakeLightingController:
    def __init__(self) -> None:
        self.power: list[bool] = []
        self.colors: list[RgbColor] = []
        self.brightness: list[int] = []

    def set_power(self, enabled: bool):
        self.power.append(enabled)
        return _done()

    def set_color(self, color: RgbColor):
        self.colors.append(color)
        return _done()

    def set_brightness(self, percent: int):
        self.brightness.append(percent)
        return _done()


def _output(red: int, green: int, blue: int, brightness: float) -> MusicLightingOutput:
    return MusicLightingOutput(RgbColor(red, green, blue), brightness)


def test_disabled_adapter_drops_outputs() -> None:
    controller = _FakeLightingController()
    adapter = MusicLightingOutputAdapter(controller)
    adapter.submit(_output(255, 0, 0, 1.0))
    assert controller.colors == []
    assert controller.brightness == []


def test_enable_and_disable_control_power() -> None:
    controller = _FakeLightingController()
    adapter = MusicLightingOutputAdapter(controller)
    adapter.set_enabled(True)
    adapter.set_enabled(False)
    assert controller.power == [True, False]


def test_small_changes_are_coalesced_by_thresholds() -> None:
    controller = _FakeLightingController()
    adapter = MusicLightingOutputAdapter(
        controller,
        max_updates_per_second=1000,
        color_threshold=10,
        brightness_threshold_percent=4,
    )
    adapter.set_enabled(True)
    adapter.submit(_output(100, 100, 100, 0.50))
    time.sleep(0.005)
    adapter.submit(_output(105, 104, 103, 0.52))
    time.sleep(0.005)
    assert controller.colors == [RgbColor(100, 100, 100)]
    assert controller.brightness == [50]
    adapter.close()


def test_burst_keeps_latest_pending_output() -> None:
    controller = _FakeLightingController()
    adapter = MusicLightingOutputAdapter(
        controller,
        max_updates_per_second=20,
        color_threshold=0,
        brightness_threshold_percent=0,
    )
    adapter.set_enabled(True)
    adapter.submit(_output(10, 0, 0, 0.10))
    adapter.submit(_output(20, 0, 0, 0.20))
    adapter.submit(_output(30, 0, 0, 0.30))
    time.sleep(0.08)
    assert controller.colors[0] == RgbColor(10, 0, 0)
    assert controller.colors[-1] == RgbColor(30, 0, 0)
    assert RgbColor(20, 0, 0) not in controller.colors
    assert controller.brightness[-1] == 30
    adapter.close()


def test_disabling_cancels_pending_burst() -> None:
    controller = _FakeLightingController()
    adapter = MusicLightingOutputAdapter(controller, max_updates_per_second=10, color_threshold=0)
    adapter.set_enabled(True)
    adapter.submit(_output(10, 0, 0, 0.10))
    adapter.submit(_output(250, 0, 0, 0.90))
    adapter.set_enabled(False)
    time.sleep(0.12)
    assert RgbColor(250, 0, 0) not in controller.colors
    assert controller.power[-1] is False
    adapter.close()
