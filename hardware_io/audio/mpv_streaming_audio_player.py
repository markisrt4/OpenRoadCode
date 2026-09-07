# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from controllers.audio.streaming_audio_player_if import StreamingAudioPlayerIf


class MpvStreamingAudioPlayer(StreamingAudioPlayerIf):
    """Play remote audio streams with an external ``mpv`` process."""

    def __init__(
        self,
        *,
        executable: str | Path = "mpv",
        stop_timeout_s: float = 3.0,
    ) -> None:
        if stop_timeout_s <= 0:
            raise ValueError("stop_timeout_s must be positive")

        self._executable = str(executable)
        self._stop_timeout_s = float(stop_timeout_s)
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def is_playing(self) -> bool:
        process = self._process
        if process is None:
            return False

        if process.poll() is None:
            return True

        self._process = None
        return False

    def play(self, stream_url: str) -> None:
        stream_url = stream_url.strip()
        if not stream_url:
            raise ValueError("stream_url must not be empty")

        executable = self._resolve_executable()
        self.stop()
        self._process = subprocess.Popen(
            [
                executable,
                "--no-video",
                "--really-quiet",
                "--",
                stream_url,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return

        process.terminate()
        try:
            process.wait(timeout=self._stop_timeout_s)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=self._stop_timeout_s)

    def _resolve_executable(self) -> str:
        executable = self._executable
        if Path(executable).is_absolute():
            if not Path(executable).is_file():
                raise RuntimeError(f"mpv executable not found: {executable}")
            return executable

        resolved = shutil.which(executable)
        if resolved is None:
            raise RuntimeError(f"mpv executable not found: {executable}")
        return resolved
