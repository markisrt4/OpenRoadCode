# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Connect optional Seesaw encoders to ORC's semantic input actions."""

import logging
from collections.abc import Callable

from common.resource_cleanup import close_resources
from config.runtime_config_models import RotaryEncoderConfig, SeesawEncoderConfig
from controllers.input.input_mapper import InputMapper
from controllers.input.rotary_encoder_input_adapter import RotaryEncoderInputAdapter
from hardware_io.rotary_encoder.rotary_encoder_if import RotaryEncoderIf
from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
    InputHandlerIf,
)
from ui.system import VolumeRequestHandlerIf
from ui.ui_action import UiAction

LOGGER = logging.getLogger(__name__)


class RotaryInput(InputHandlerIf):
    """Own the polling adapters and deliver their actions on the UI thread."""

    def __init__(
        self,
        encoders: tuple[RotaryEncoderIf, RotaryEncoderIf],
        dispatch_ui: Callable[[Callable[[], None]], None],
        screen_action: Callable[[UiAction], None],
        volume: VolumeRequestHandlerIf | None,
    ) -> None:
        volume_id = InputDeviceId(InputDeviceType.ROTARY_ENCODER, 0)
        screen_id = InputDeviceId(InputDeviceType.ROTARY_ENCODER, 1)
        self._mapper = InputMapper(screen_id, volume_id)
        self._adapters = tuple(
            RotaryEncoderInputAdapter(encoder, device_id, self)
            for encoder, device_id in zip(encoders, (volume_id, screen_id), strict=True)
        )
        self._dispatch_ui = dispatch_ui
        self._screen_action = screen_action
        self._volume = volume
        self._active = False

    def start(self) -> None:
        self._active = True
        for adapter in self._adapters:
            try:
                adapter.connect()
            except (OSError, RuntimeError, ValueError):
                LOGGER.exception("Could not start a configured ORC rotary encoder")

    def close(self) -> None:
        self._active = False
        close_resources(*(adapter.disconnect for adapter in self._adapters))

    def handle_input_event(self, event: InputEvent) -> None:
        if not self._active or event.event_type is not InputEventType.ROTATED:
            return
        action = self._mapper.map_input(event)
        if action is not None:
            steps = abs(int(event.value))
            self._dispatch_ui(lambda: self._apply(action, steps))

    def _apply(self, action: UiAction, steps: int) -> None:
        if not self._active:
            return
        for _ in range(steps):
            if action is UiAction.VOLUME_UP:
                if self._volume is not None:
                    self._volume.request_volume_up()
            elif action is UiAction.VOLUME_DOWN:
                if self._volume is not None:
                    self._volume.request_volume_down()
            else:
                self._screen_action(action)


def create_rotary_input(
    addresses: str | None,
    dispatch_ui: Callable[[Callable[[], None]], None],
    screen_action: Callable[[UiAction], None],
    volume: VolumeRequestHandlerIf | None,
    *,
    config: RotaryEncoderConfig | None = None,
) -> RotaryInput | None:
    if addresses:
        try:
            volume_address, screen_address = (
                int(value.strip(), 0) for value in addresses.split(",")
            )
            if volume_address == screen_address or not all(
                0x08 <= address <= 0x77 for address in (volume_address, screen_address)
            ):
                raise ValueError
        except ValueError as exc:
            raise ValueError("ORC_ROTARY_ENCODERS requires two distinct I²C addresses") from exc
        volume_encoder = SeesawEncoderConfig(volume_address)
        screen_encoder = SeesawEncoderConfig(screen_address)
    else:
        if config is None or config.screen_index is None:
            return None
        volume_device = config.devices[config.volume_index]
        screen_device = config.devices[config.screen_index]
        if not isinstance(volume_device, SeesawEncoderConfig) or not isinstance(
            screen_device, SeesawEncoderConfig
        ):
            raise ValueError("ORC rotary volume_index and screen_index must select Seesaw encoders")
        volume_encoder, screen_encoder = volume_device, screen_device

    try:
        import board

        from hardware_io.rotary_encoder.seesaw_rotary_encoder import SeesawRotaryEncoder

        bus = board.I2C()
    except (ImportError, OSError, RuntimeError):
        LOGGER.exception("Could not open I²C for configured ORC rotary encoders")
        return None
    volume_knob, screen_knob = (
        SeesawRotaryEncoder(
            address=device.address, i2c=bus, reverse_direction=device.reverse_direction
        )
        for device in (volume_encoder, screen_encoder)
    )
    return RotaryInput((volume_knob, screen_knob), dispatch_ui, screen_action, volume)
