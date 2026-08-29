# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Linux/PipeWire adapter for the refreshed music-analysis pipeline."""
from __future__ import annotations

from dataclasses import asdict
import threading

from controllers.audio.capture import PipewireAudioCapture
from controllers.audio.music_analysis import (
    MusicAnalysisConsumer,
    MusicAnalysisPipeline,
    MusicAnalysisState,
    MusicAnalyzer,
)


class WebLinuxAudioAnalysisSession:
    """Capture Linux system audio and expose the latest shared analysis state."""

    def __init__(
        self,
        *,
        capture: PipewireAudioCapture | None = None,
        consumer: MusicAnalysisConsumer | None = None,
    ) -> None:
        self._capture = capture or PipewireAudioCapture()
        self._analyzer = MusicAnalyzer()
        self._consumer = consumer
        self._lock = threading.RLock()
        self._latest: MusicAnalysisState | None = None
        self._pipeline = MusicAnalysisPipeline(
            self._capture,
            self._analyzer,
            self._on_state,
        )

    def start(self) -> dict[str, object]:
        """Start PipeWire capture."""
        if not self._pipeline.is_running:
            self._pipeline.start()
        return self.state()

    def stop(self) -> dict[str, object]:
        """Stop PipeWire capture."""
        if self._pipeline.is_running:
            self._pipeline.stop()
        return self.state()

    def state(self) -> dict[str, object]:
        """Return capture and latest analysis state."""
        with self._lock:
            latest = self._latest
        if latest is None:
            data: dict[str, object] = {
                "level": 0.0,
                "bass": 0.0,
                "mid": 0.0,
                "treble": 0.0,
                "spectrum": [0.0] * self._analyzer.band_count,
                "percussion": {
                    "kick": 0.0,
                    "bass": 0.0,
                    "snare": 0.0,
                    "tom_high": 0.0,
                    "tom_mid": 0.0,
                    "tom_low": 0.0,
                    "cymbal": 0.0,
                },
                "sample_rate_hz": 0,
                "fft_size": self._analyzer.fft_size,
            }
        else:
            data = asdict(latest)
            data["spectrum"] = list(latest.spectrum)
        data["running"] = self._pipeline.is_running
        data["zeroized"] = self._pipeline.is_zeroized
        data["source"] = "linux-pipewire"
        return data

    def start_zeroize(self) -> dict[str, object]:
        """Begin ambient-noise calibration."""
        self._pipeline.start_zeroize()
        return self.state()

    def finish_zeroize(self) -> dict[str, object]:
        """Finish ambient-noise calibration."""
        self._pipeline.finish_zeroize()
        return self.state()

    def clear_zeroize(self) -> dict[str, object]:
        """Clear ambient-noise calibration."""
        self._pipeline.clear_zeroize()
        return self.state()

    def _on_state(self, state: MusicAnalysisState) -> None:
        with self._lock:
            self._latest = state
        if self._consumer is not None:
            self._consumer(state)
