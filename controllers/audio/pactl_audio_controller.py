"""Audio output control using the PulseAudio-compatible pactl client."""

from __future__ import annotations

import re
import subprocess

from controllers.audio.audio_controller_if import AudioControllerIf


class PactlAudioController(AudioControllerIf):
    """Control the default Linux development-host audio sink with pactl."""

    DEFAULT_SINK = "@DEFAULT_SINK@"

    def __init__(
        self,
        *,
        steps: int = 20,
        sink: str = DEFAULT_SINK,
    ) -> None:
        if steps <= 0:
            raise ValueError("steps must be greater than zero")
        self._steps = steps
        self._sink = sink

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_message(self) -> str | None:
        return None

    @property
    def maximum_level(self) -> int:
        return self._steps

    def volume_up(self) -> int:
        return self.set_volume_level(self.get_volume_level() + 1)

    def volume_down(self) -> int:
        return self.set_volume_level(self.get_volume_level() - 1)

    def get_volume_level(self) -> int:
        output = self._run(["get-sink-volume", self._sink], capture=True)
        match = re.search(r"/\s*(\d+)%", output)
        if match is None:
            raise RuntimeError(f"Unexpected pactl volume response: {output!r}")
        return self._clamp_level(round(int(match.group(1)) * self._steps / 100))

    def set_volume_level(self, level: int) -> int:
        clamped = self._clamp_level(level)
        percent = round(clamped * 100 / self._steps)
        self._run(["set-sink-volume", self._sink, f"{percent}%"])
        return clamped

    def is_muted(self) -> bool:
        output = self._run(["get-sink-mute", self._sink], capture=True)
        return output.strip().lower().endswith("yes")

    def toggle_mute(self) -> bool:
        self._run(["set-sink-mute", self._sink, "toggle"])
        return self.is_muted()

    def _clamp_level(self, level: int) -> int:
        return max(0, min(level, self._steps))

    @staticmethod
    def _run(args: list[str], *, capture: bool = False) -> str:
        try:
            result = subprocess.run(
                ["pactl", *args],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("pactl was not found") from exc
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip() or exc.stdout.strip() or "unknown error"
            raise RuntimeError(f"pactl failed: {message}") from exc
        return result.stdout if capture else ""
