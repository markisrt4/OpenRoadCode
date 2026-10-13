# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Expose cached native analyzer frames through the compact Home contract."""

from __future__ import annotations

from collections.abc import Callable
from time import monotonic

from ui.music_visualizer import MusicVisualizerSource, VisualizerFrame
from ui.music_visualizer.home_spectrum_ui_if import HomeSpectrumState
from ui.music_visualizer.music_visualizer_control_if import MusicVisualizerControlIf
from ui.music_visualizer.music_visualizer_types import MusicCaptureState


class NativeHomeSpectrumFeed:
    """Adapt controller-owned capture without performing work in the frontend."""

    def __init__(
        self,
        controller: MusicVisualizerControlIf,
        *,
        default_source: MusicVisualizerSource,
        clock: Callable[[], float] = monotonic,
        freshness_s: float = 0.75,
    ) -> None:
        self._controller = controller
        self._default_source = default_source
        self._clock = clock
        self._freshness_s = freshness_s
        self._owner = f"home-spectrum-{id(self)}"
        self._attached = False
        self._last_frame: VisualizerFrame | None = None
        self._last_frame_at: float | None = None

    def attach_home(self) -> None:
        if not self._attached:
            self._attached = True
            self._controller.attach_view(self._owner)

    def detach_home(self) -> None:
        if self._attached:
            self._attached = False
            self._controller.detach_view(self._owner)

    def read_spectrum(self) -> HomeSpectrumState:
        now = self._clock()
        frame = self._controller.latest_frame()
        if frame is not None and frame is not self._last_frame:
            self._last_frame = frame
            self._last_frame_at = now
        capture = self._controller.capture_state()
        running = capture is MusicCaptureState.RUNNING
        busy = capture is MusicCaptureState.STARTING
        fresh = (
            frame is not None
            and self._last_frame_at is not None
            and now - self._last_frame_at <= self._freshness_s
        )
        return HomeSpectrumState(
            bands=frame.spectrum if fresh and frame is not None else (),
            active=bool(fresh and frame is not None and frame.spectrum),
            running=running,
            busy=busy,
        )

    def request_start_spectrum(self) -> None:
        self._controller.start(
            self._controller.selected_source() or self._default_source
        )

    def request_stop_spectrum(self) -> None:
        self._controller.stop()
