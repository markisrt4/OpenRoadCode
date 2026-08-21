# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Background Linux system-audio analysis for the Web visualizer."""
from __future__ import annotations

from dataclasses import asdict
import threading
import time

from controllers.audio_analysis.audio_analysis import AudioAnalyzer, AudioAnalysisState
from hardware_io.audio.pipewire_audio_capture import PipeWireAudioCapture


class WebLinuxAudioAnalysisSession:
    """Continuously analyze the default Linux PipeWire monitor source."""

    def __init__(self) -> None:
        self._capture = PipeWireAudioCapture()
        self._analyzer = AudioAnalyzer(spectrum_band_count=24)
        self._lock = threading.RLock()
        self._state = AudioAnalysisState(0.0, 0.0, 0.0, 0.0, 0.0, ())
        self._running = False
        self._thread: threading.Thread | None = None
        self._error: str | None = None

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    def start(self) -> dict[str, object]:
        with self._lock:
            if self._running:
                return self.state()
            self._capture.start()
            self._running = True
            self._error = None
            self._thread = threading.Thread(
                target=self._run,
                name="openroadcode-linux-audio-analysis",
                daemon=True,
            )
            self._thread.start()
        return self.state()

    def stop(self) -> dict[str, object]:
        with self._lock:
            self._running = False
        self._capture.stop()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None
        return self.state()

    def _run(self) -> None:
        try:
            while self.running:
                frame = self._capture.read()
                state = self._analyzer.analyze(frame)
                with self._lock:
                    self._state = state
        except Exception as exc:
            with self._lock:
                self._error = str(exc)
                self._running = False
            self._capture.stop()

    def state(self) -> dict[str, object]:
        with self._lock:
            state = asdict(self._state)
            state["spectrum"] = list(self._state.spectrum)
            state.update(
                running=self._running,
                source="linux-pipewire",
                error=self._error,
                timestamp=time.time(),
            )
            return state
