# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Share explicitly started analysis across browser/Home view transitions."""
from collections.abc import Callable, Mapping, Sequence
from math import isfinite
from threading import RLock, Timer
from time import monotonic

from controllers.audio.capture.audio_capture_if import AudioCaptureIf
from ui.music_visualizer.home_spectrum_ui_if import HomeSpectrumState
from .music_analysis_session import MusicAnalysisSession


class SharedMusicAnalysisSession(MusicAnalysisSession):
    """One capture with cached presentation and a short view-handoff grace period."""

    def __init__(self, sources: Mapping[str, Callable[[], AudioCaptureIf]], *,
                 clock: Callable[[], float] = monotonic) -> None:
        super().__init__(sources)
        self._snapshot_lock = RLock()
        self._clock = clock
        self._snapshot = HomeSpectrumState()
        self._received = 0.0
        self._home_count = 0
        self._browser_visible = False
        self._closed = False
        self._release: Timer | None = None
        self._release_generation = 0

    def _on_samples(self, generation: int, samples: Sequence[float], sample_rate_hz: int) -> None:
        # Publish inside the capture-generation lock: stopped callbacks cannot
        # overwrite the next session's snapshot.
        with self._lock:
            super()._on_samples(generation, samples, sample_rate_hz)
            if generation != self._generation or self._latest is None:
                return
            bands = tuple(max(0.0, min(1.0, value)) if isfinite(value) else 0.0
                          for value in self._latest.spectrum)
            with self._snapshot_lock:
                if not self._closed:
                    self._snapshot = HomeSpectrumState(bands, True)
                    self._received = self._clock()

    def read_spectrum(self) -> HomeSpectrumState:
        """Read a small cache, never waiting for capture or an FFT."""
        with self._snapshot_lock:
            if self._closed or self._clock() - self._received > 0.75:
                return HomeSpectrumState()
            return self._snapshot

    def start(self, source: str | None = None) -> dict[str, object]:
        with self._lifecycle:
            if self._closed:
                raise RuntimeError("Shared analysis is closed")
            return super().start(source)

    def stop(self, *, source: str | None = None) -> dict[str, object]:
        with self._lifecycle:
            with self._lock:
                matches = source is None or source == self._source
            result = super().stop(source=source)
            if matches:
                with self._snapshot_lock:
                    self._snapshot = HomeSpectrumState()
            return result

    def _cancel_release(self) -> None:
        self._release_generation += 1
        if self._release is not None:
            self._release.cancel()
            self._release = None

    def attach_home(self) -> None:
        with self._snapshot_lock:
            if not self._closed:
                self._home_count += 1
                self._cancel_release()

    def detach_home(self) -> None:
        with self._snapshot_lock:
            self._home_count = max(0, self._home_count - 1)
            self._schedule_release()

    def attach_browser(self) -> None:
        with self._snapshot_lock:
            if not self._closed:
                self._browser_visible = True
                self._cancel_release()

    def detach_browser(self) -> None:
        with self._snapshot_lock:
            self._browser_visible = False
            self._schedule_release()

    def _schedule_release(self) -> None:
        if self._closed or self._home_count or self._browser_visible:
            return
        self._cancel_release()
        self._release = Timer(0.25, self._stop_if_idle, (self._release_generation,))
        self._release.daemon = True
        self._release.start()

    def _stop_if_idle(self, generation: int) -> None:
        with self._lifecycle:
            with self._snapshot_lock:
                if (self._closed or generation != self._release_generation
                        or self._home_count or self._browser_visible):
                    return
            self.stop()

    def close(self) -> None:
        """Cancel delayed release and stop the owned capture exactly once."""
        with self._lifecycle:
            with self._snapshot_lock:
                if self._closed:
                    return
                self._closed = True
                self._cancel_release()
            self.stop()
