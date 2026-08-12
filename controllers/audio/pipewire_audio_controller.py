# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import re
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
        sink: str = DEFAULT_SINK,
    ) -> None:
        if steps <= 0:
            raise ValueError("steps must be greater than zero")

        if not 1 <= step_percent <= 100:
            raise ValueError(
                "step_percent must be in range 1..100"
            )

        self._steps = steps
        self._step_percent = step_percent
        self._sink = sink
        self._current_level: int | None = None

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_message(self) -> str | None:
        return None

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
        return self.adjust_volume(1)

    def volume_down(self) -> int:
        return self.adjust_volume(-1)

    def adjust_volume(self, steps: int) -> int:
        """Adjust multiple volume steps with one PipeWire command."""
        if steps == 0:
            return self.get_volume_level()

        percent = abs(steps) * self._step_percent
        adjustment = f"{percent}%{'+' if steps > 0 else '-'}"
        args = [
            "set-volume",
            self._sink,
            adjustment,
        ]
        if steps > 0:
            args.extend(["--limit", str(self.MAX_VOLUME)])
        self._run_wpctl(args)

        if self._current_level is None:
            return self.get_volume_level()
        self._current_level = self._clamp_level(
            self._current_level + steps
        )
        return self._current_level

    def get_volume_level(self) -> int:
        output = self._run_wpctl(
            [
                "get-volume",
                self._sink,
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

        self._current_level = self._clamp_level(
            round(volume * self._steps)
        )
        return self._current_level

    def set_volume_level(self, level: int) -> int:
        clamped_level = self._clamp_level(level)
        volume = clamped_level / self._steps

        self._run_wpctl(
            [
                "set-volume",
                self._sink,
                str(volume),
            ]
        )
        self._current_level = clamped_level
        return clamped_level

    def is_muted(self) -> bool:
        output = self._run_wpctl(
            [
                "get-volume",
                self._sink,
            ],
            capture=True,
        )
        return "[MUTED]" in output.upper()

    def toggle_mute(self) -> bool:
        self._run_wpctl(
            [
                "set-mute",
                self._sink,
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
            return PipewireAudioController._run_pactl_for_wpctl(
                args,
                capture=capture,
                wpctl_error=exc,
            )

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

    @staticmethod
    def _run_pactl_for_wpctl(
        args: list[str],
        *,
        capture: bool,
        wpctl_error: FileNotFoundError,
    ) -> str:
        """Translate supported wpctl operations to pactl commands."""
        operation = args[0]
        sink = "@DEFAULT_SINK@"
        if operation == "get-volume":
            volume_output = PipewireAudioController._run_pactl(
                ["get-sink-volume", sink],
                capture=True,
                wpctl_error=wpctl_error,
            )
            match = re.search(r"/\s*(\d+)%", volume_output)
            if match is None:
                raise RuntimeError(
                    f"Unexpected pactl volume response: {volume_output!r}"
                )
            mute_output = PipewireAudioController._run_pactl(
                ["get-sink-mute", sink],
                capture=True,
                wpctl_error=wpctl_error,
            )
            muted = mute_output.strip().lower().endswith("yes")
            suffix = " [MUTED]" if muted else ""
            return f"Volume: {int(match.group(1)) / 100:.2f}{suffix}"

        if operation == "set-mute":
            pactl_args = ["set-sink-mute", sink, args[2]]
        elif operation == "set-volume":
            value = args[2]
            if value.endswith("+"):
                value = f"+{value[:-1]}"
            elif value.endswith("-"):
                value = f"-{value[:-1]}"
            elif "%" not in value:
                value = f"{round(float(value) * 100)}%"
            pactl_args = ["set-sink-volume", sink, value]
        else:
            raise RuntimeError(f"Unsupported pactl audio operation: {operation}")

        return PipewireAudioController._run_pactl(
            pactl_args,
            capture=capture,
            wpctl_error=wpctl_error,
        )

    @staticmethod
    def _run_pactl(
        args: list[str],
        *,
        capture: bool,
        wpctl_error: FileNotFoundError,
    ) -> str:
        try:
            result = subprocess.run(
                ["pactl", *args],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Neither wpctl nor pactl was found"
            ) from wpctl_error
        except subprocess.CalledProcessError as exc:
            message = (
                exc.stderr.strip()
                or exc.stdout.strip()
                or "unknown pactl error"
            )
            raise RuntimeError(f"pactl failed: {message}") from exc
        return result.stdout if capture else ""
