from __future__ import annotations

import subprocess

from controllers.audio.audio_controller_if import AudioControllerIf


class PipewireAudioController(AudioControllerIf):
    """
    Controls the default PipeWire audio sink using wpctl.
    """

    DEFAULT_SINK = "@DEFAULT_AUDIO_SINK@"
    MAX_VOLUME = 1.0

    def __init__(
        self,
        *,
        steps: int = 20,
        step_percent: int = 5,
    ) -> None:
        if steps <= 0:
            raise ValueError("steps must be greater than zero")

        if not 1 <= step_percent <= 100:
            raise ValueError(
                "step_percent must be in range 1..100"
            )

        self._steps = steps
        self._step_percent = step_percent

    @property
    def steps(self) -> int:
        """Return the number of discrete volume steps.

        @return Count of selectable volume levels.
        """
        return self._steps

    @property
    def maximum_level(self) -> int:
        return self._steps

    def volume_up(self) -> int:
        self._run_wpctl(
            [
                "set-volume",
                self.DEFAULT_SINK,
                f"{self._step_percent}%+",
                "--limit",
                str(self.MAX_VOLUME),
            ]
        )

        return self.get_volume_level()

    def volume_down(self) -> int:
        self._run_wpctl(
            [
                "set-volume",
                self.DEFAULT_SINK,
                f"{self._step_percent}%-",
            ]
        )

        return self.get_volume_level()

    def get_volume_level(self) -> int:
        output = self._run_wpctl(
            [
                "get-volume",
                self.DEFAULT_SINK,
            ],
            capture=True,
        )

        # Typical output:
        # Volume: 0.62
        # Volume: 0.62 [MUTED]
        parts = output.strip().split()

        if len(parts) < 2:
            raise RuntimeError(
                f"Unexpected wpctl response: {output!r}"
            )

        try:
            volume = float(parts[1])
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid wpctl volume response: {output!r}"
            ) from exc

        return self._clamp_level(
            round(volume * self._steps)
        )

    def set_volume_level(self, level: int) -> int:
        clamped_level = self._clamp_level(level)
        volume = clamped_level / self._steps

        self._run_wpctl(
            [
                "set-volume",
                self.DEFAULT_SINK,
                str(volume),
            ]
        )

        return self.get_volume_level()

    def is_muted(self) -> bool:
        output = self._run_wpctl(
            [
                "get-volume",
                self.DEFAULT_SINK,
            ],
            capture=True,
        )
        return "[MUTED]" in output.upper()

    def toggle_mute(self) -> bool:
        self._run_wpctl(
            [
                "set-mute",
                self.DEFAULT_SINK,
                "toggle",
            ]
        )
        return self.is_muted()

    def _clamp_level(self, level: int) -> int:
        return max(0, min(level, self._steps))

    @staticmethod
    def _run_wpctl(
        args: list[str],
        *,
        capture: bool = False,
    ) -> str:
        try:
            result = subprocess.run(
                ["wpctl", *args],
                capture_output=True,
                text=True,
                check=True,
            )

        except FileNotFoundError as exc:
            raise RuntimeError(
                "wpctl was not found"
            ) from exc

        except subprocess.CalledProcessError as exc:
            message = (
                exc.stderr.strip()
                or exc.stdout.strip()
                or "unknown wpctl error"
            )

            raise RuntimeError(
                f"wpctl failed: {message}"
            ) from exc

        return result.stdout if capture else ""
