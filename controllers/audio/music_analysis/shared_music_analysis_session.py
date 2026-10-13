# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Share explicitly started analysis across browser/Home view transitions."""
from collections.abc import Callable, Mapping, Sequence
from math import isfinite
from dataclasses import replace
from threading import RLock, Thread, Timer
from time import monotonic

from controllers.audio.capture.audio_capture_if import AudioCaptureIf
from ui.music_visualizer.home_spectrum_ui_if import HomeSpectrumState
from .music_analysis_session import MusicAnalysisSession


class SharedMusicAnalysisSession(MusicAnalysisSession):
    """One capture with cached presentation and a short view-handoff grace period."""

    def __init__(self, sources: Mapping[str, Callable[[], AudioCaptureIf]], *,
                 clock: Callable[[], float] = monotonic,
                 run_work: Callable[[Callable[[], None]], None] | None = None) -> None:
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
        self._run_work = run_work or self._launch_worker
        self._request_generation = 0

    @staticmethod
    def _launch_worker(work: Callable[[], None]) -> None:
        Thread(target=work, name="orc-home-spectrum", daemon=True).start()

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
                    self._snapshot = replace(self._snapshot, bands=bands, active=True)
                    self._received = self._clock()

    def read_spectrum(self) -> HomeSpectrumState:
        """Read a small cache, never waiting for capture or an FFT."""
        with self._snapshot_lock:
            if self._closed:
                return HomeSpectrumState()
            if self._clock() - self._received > 0.75:
                return replace(self._snapshot, bands=(), active=False)
            return self._snapshot

    def start(self, source: str | None = None) -> dict[str, object]:
        with self._lifecycle:
            if self._closed:
                raise RuntimeError("Shared analysis is closed")
            result = super().start(source)
            with self._snapshot_lock:
                self._snapshot = replace(self._snapshot, running=True, message="")
            return result

    def stop(self, *, source: str | None = None) -> dict[str, object]:
        with self._lifecycle:
            with self._lock:
                matches = source is None or source == self._source
            result = super().stop(source=source)
            if matches:
                with self._snapshot_lock:
                    self._snapshot = replace(self._snapshot, bands=(), active=False,
                                             running=False, message="")
            return result

    def request_start_spectrum(self) -> None:
        """Start the available platform source without blocking the UI."""
        self._request_capture(True)

    def request_stop_spectrum(self) -> None:
        """Stop shared capture without blocking the UI."""
        self._request_capture(False)

    def _request_capture(self, start: bool) -> None:
        with self._snapshot_lock:
            if self._closed or self._snapshot.busy:
                return
            self._request_generation += 1
            generation = self._request_generation
            self._snapshot = replace(self._snapshot, busy=True, message="")

        def work() -> None:
            message = ""
            try:
                with self._lifecycle:
                    with self._snapshot_lock:
                        if self._closed or generation != self._request_generation:
                            return
                        if start and not self._home_count:
                            return
                    if start:
                        source = next((name for name in ("android-playback", "linux-pipewire")
                                       if name in self._sources), None)
                        if source is None:
                            raise RuntimeError("Open Visualizer to set up audio capture")
                        self.start(source)
                    else:
                        self.stop()
            except Exception as exc:
                message = str(exc)
            finally:
                with self._snapshot_lock:
                    if not self._closed and generation == self._request_generation:
                        self._snapshot = replace(self._snapshot, busy=False, message=message)

        try:
            self._run_work(work)
        except Exception as exc:
            with self._snapshot_lock:
                self._snapshot = replace(self._snapshot, busy=False, message=str(exc))

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
            if not self._home_count:
                self._request_generation += 1
                self._snapshot = replace(self._snapshot, busy=False)
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
                self._request_generation += 1
                self._cancel_release()
            self.stop()
