from __future__ import annotations

from concurrent.futures import Future

from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.lighting.lighting_types import (
    CustomPatternMode,
    LightingState,
    RgbColor,
)


class LightingControllerStub(LightingControllerIf):
    """Minimal no-op lighting controller."""

    def __init__(
        self,
        state: LightingState | None = None,
    ) -> None:
        self._state = state or LightingState()

    @property
    def is_connected(self) -> bool:
        return self._state.connected

    def current_state(self) -> LightingState:
        return self._state

    def connect(self) -> Future[None]:
        return self._result()

    def disconnect(self) -> Future[None]:
        return self._completed()

    def close(self) -> None:
        pass

    def set_power(self, enabled: bool) -> Future[None]:
        return self._result()

    def set_color(self, color: RgbColor) -> Future[None]:
        return self._result()

    def set_brightness(self, percent: int) -> Future[None]:
        return self._result()

    def set_color_temperature(self, percent: int) -> Future[None]:
        return self._result()

    def set_pattern(self, pattern_index: int) -> Future[None]:
        return self._result()

    def set_music_mode(self, eq_mode: int) -> Future[None]:
        return self._result()

    def set_custom_pattern_mode(
        self,
        mode: CustomPatternMode,
    ) -> Future[None]:
        return self._result()

    def set_custom_pattern_direction(
        self,
        is_forward: bool,
    ) -> Future[None]:
        return self._result()

    def _result(self) -> Future[None]:
        return self._completed()

    @staticmethod
    def _completed() -> Future[None]:
        future: Future[None] = Future()
        future.set_result(None)
        return future
