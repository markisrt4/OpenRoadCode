"""Dependencies required to assemble the Car UI frontend."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import logging

from apps.carUi.runtime.car_ui_runtime import CarUiRuntime
from controllers.audio.audio_controller_if import AudioControllerIf
from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.navigation import (
    NavigationControllerIf,
    PositionSourceIf,
    UnconfiguredNavigationController,
)
from controllers.spotify import SpotifyControllerIf
from hardware_io.rotary_encoder import RotaryEncoderIf
from hardware_io.buttons.push_button_if import PushButtonIf
from hardware_io.keyboard import KeyboardReaderIf


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CarUiDependencies:
    """Controller and hardware objects supplied to the Car UI."""

    runtime: CarUiRuntime
    position_source: PositionSourceIf
    audio_controller: AudioControllerIf
    spotify_controller: SpotifyControllerIf
    lighting_controller: LightingControllerIf
    rotary_encoders: Sequence[RotaryEncoderIf]
    volume_encoder_index: int
    navigation_controller: NavigationControllerIf = field(
        default_factory=UnconfiguredNavigationController
    )
    keyboards: Sequence[KeyboardReaderIf] = ()
    push_buttons: Sequence[PushButtonIf] = ()
    push_button_actions: Sequence[str] = ()
    _closed: bool = field(default=False, init=False, repr=False, compare=False)

    def close(self) -> None:
        """Release dependencies owned by the application bootstrap."""
        if self._closed:
            return
        object.__setattr__(self, "_closed", True)

        for index, encoder in enumerate(self.rotary_encoders):
            self._close_resource(f"rotary encoder {index}", encoder.stop)
        for index, keyboard in enumerate(self.keyboards):
            self._close_resource(f"keyboard {index}", keyboard.close)
        for index, button in enumerate(self.push_buttons):
            self._close_resource(f"pushbutton {index}", button.stop)
        self._close_resource("Car UI runtime", self.runtime.close)
        self._close_resource("navigation controller", self.navigation_controller.stop)
        self._close_resource("lighting controller", self.lighting_controller.close)
        self._close_resource("position source", self.position_source.stop)

    @staticmethod
    def _close_resource(name: str, close: Callable[[], object]) -> None:
        try:
            close()
        except Exception:
            LOGGER.exception("Failed to close %s", name)
