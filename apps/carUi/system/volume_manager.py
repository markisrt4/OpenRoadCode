from __future__ import annotations

from collections.abc import Callable


class VolumeManager:
    """Coordinate audio volume operations with UI state updates."""

    def __init__(
        self,
        *,
        audio_controller,
        indicator_steps: int,
        set_volume_level: Callable[[int], None],
        set_muted: Callable[[bool], None],
        set_status: Callable[[str], None],
    ) -> None:
        if indicator_steps <= 0:
            raise ValueError("indicator_steps must be greater than zero")

        self._audio_controller = audio_controller
        self._indicator_steps = indicator_steps
        self._set_volume_level = set_volume_level
        self._set_muted = set_muted
        self._set_status = set_status

    def get_level(self) -> int:
        return self._audio_controller.get_volume_level()

    def get_indicator_level(self) -> int:
        return self.indicator_level(
            self.get_level(),
            maximum_level=self._audio_controller.maximum_level,
            indicator_steps=self._indicator_steps,
        )

    def is_muted(self) -> bool:
        return self._audio_controller.is_muted()

    def toggle_mute(self) -> None:
        try:
            muted = self._audio_controller.toggle_mute()
            self._set_muted(muted)
            self._set_status("Volume muted" if muted else "Volume unmuted")
        except Exception as exc:
            self._set_status(f"Mute toggle failed: {exc}")
            print(f"[VOLUME] Mute toggle failed: {exc}")

    def volume_up(self) -> None:
        try:
            level = self._audio_controller.volume_up()
            self._publish_indicator_level(level)
            self._set_status("Volume up")
        except Exception as exc:
            self._set_status(f"Volume up failed: {exc}")
            print(f"[VOLUME] Volume up failed: {exc}")

    def volume_down(self) -> None:
        try:
            level = self._audio_controller.volume_down()
            self._publish_indicator_level(level)
            self._set_status("Volume down")
        except Exception as exc:
            self._set_status(f"Volume down failed: {exc}")
            print(f"[VOLUME] Volume down failed: {exc}")

    def _publish_indicator_level(self, audio_level: int) -> None:
        self._set_volume_level(
            self.indicator_level(
                audio_level,
                maximum_level=self._audio_controller.maximum_level,
                indicator_steps=self._indicator_steps,
            )
        )

    @staticmethod
    def indicator_level(
        audio_level: int,
        *,
        maximum_level: int,
        indicator_steps: int,
    ) -> int:
        if maximum_level <= 0:
            raise ValueError("maximum_level must be greater than zero")
        if indicator_steps <= 0:
            raise ValueError("indicator_steps must be greater than zero")

        clamped_level = max(0, min(audio_level, maximum_level))
        return (
            clamped_level * indicator_steps
            + maximum_level
            - 1
        ) // maximum_level
