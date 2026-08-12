#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from pathlib import Path

from config.runtime_config import (
    RuntimeConfigParser,
    RotaryEncoderConfig,
)
from apps.carUi.runtime.car_ui_input_runtime import CarUiInputRuntime
from apps.carUi.runtime.rotary_encoder_runtime import (
    create_rotary_encoder_runtime,
)
from input_events import InputDeviceId, InputDeviceType
from controllers.audio import PipewireAudioController
from controllers.input import (
    InputManager,
    InputMapper,
)
from ui.ui_action import UiAction
from ui.ui_event_handler_if import UiEventHandlerIf


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "runtime.toml"
DEFAULT_VOLUME_STEPS = 20


class CliScheduler:
    """Small toolkit-neutral scheduler used to drive the input runtime."""

    def __init__(self) -> None:
        self._next_id = 0
        self._callbacks: dict[
            str,
            tuple[float, Callable[[], None]],
        ] = {}

    def dispatch_ui(self, callback: Callable[[], None]) -> None:
        callback()

    def schedule_ui_callback(
        self,
        delay_ms: int,
        callback: Callable[[], None],
    ) -> str:
        self._next_id += 1
        callback_id = f"after-{self._next_id}"
        deadline = time.monotonic() + (delay_ms / 1000)
        self._callbacks[callback_id] = (deadline, callback)
        return callback_id

    def cancel_ui_callback(self, callback_id: object) -> None:
        self._callbacks.pop(callback_id, None)

    def run_pending(self) -> None:
        now = time.monotonic()
        ready = tuple(
            (
                callback_id,
                callback,
            )
            for callback_id, (deadline, callback) in self._callbacks.items()
            if deadline <= now
        )

        for callback_id, callback in ready:
            self._callbacks.pop(callback_id, None)
            callback()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test the configured Car UI volume encoder against the "
            "system PipeWire volume"
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Car UI runtime TOML (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=f"Project root (default: {PROJECT_ROOT})",
    )
    parser.add_argument(
        "--volume-steps",
        type=int,
        default=DEFAULT_VOLUME_STEPS,
        help=(
            "Number of discrete reported volume levels "
            f"(default: {DEFAULT_VOLUME_STEPS})"
        ),
    )
    parser.add_argument(
        "--step-percent",
        type=int,
        default=5,
        help="PipeWire percentage adjustment per encoder step",
    )
    return parser.parse_args()


def select_volume_encoder(
    config: RotaryEncoderConfig,
) -> RotaryEncoderConfig:
    """Return a runtime config containing only the selected volume device."""
    return RotaryEncoderConfig(
        devices=(config.devices[config.volume_index],),
        volume_index=0,
    )


def main() -> None:
    args = parse_args()
    config = RuntimeConfigParser(
        args.config,
        project_root=args.project_root,
    ).load()
    configured_encoders = config.input.rotary_encoders
    configured_volume_index = configured_encoders.volume_index
    encoder_runtime = create_rotary_encoder_runtime(
        select_volume_encoder(configured_encoders)
    )
    audio_controller = PipewireAudioController(
        steps=args.volume_steps,
        step_percent=args.step_percent,
    )
    scheduler = CliScheduler()

    def volume_up() -> None:
        level = audio_controller.volume_up()
        print(f"Volume up   -> level {level}/{audio_controller.steps}")

    def volume_down() -> None:
        level = audio_controller.volume_down()
        print(f"Volume down -> level {level}/{audio_controller.steps}")

    def toggle_mute() -> None:
        muted = audio_controller.toggle_mute()
        print("Audio muted" if muted else "Audio unmuted")

    class VolumeActionHandler(UiEventHandlerIf):
        def handle_ui_action(self, action: UiAction) -> None:
            actions = {
                UiAction.VOLUME_UP: volume_up,
                UiAction.VOLUME_DOWN: volume_down,
                UiAction.VOLUME_MUTE: toggle_mute,
            }
            callback = actions.get(action)
            if callback is not None:
                callback()

    volume_encoder_id = InputDeviceId(
        InputDeviceType.ROTARY_ENCODER,
        encoder_runtime.volume_index,
    )
    input_manager = InputManager(
        mapper=InputMapper(
            user_encoder_id=(),
            volume_encoder_id=volume_encoder_id,
        ),
        ui_handler=VolumeActionHandler(),
    )

    input_runtime = CarUiInputRuntime(
        dispatcher=scheduler,
        encoders=encoder_runtime.encoders,
        device_ids=(volume_encoder_id,),
        input_handler=input_manager,
    )

    initial_level = audio_controller.get_volume_level()
    print("Car UI volume encoder component test")
    print(f"Config: {args.config.resolve()}")
    print(
        "Volume encoder device index: "
        f"{configured_volume_index}"
    )
    print(
        f"Initial system volume: "
        f"{initial_level}/{audio_controller.steps}"
    )
    print(
        "Initial mute state: "
        f"{'muted' if audio_controller.is_muted() else 'unmuted'}"
    )
    print("Rotate the configured volume encoder or press it to toggle mute.")
    print("Press Ctrl+C to stop.\n")

    input_runtime.start()

    try:
        while True:
            scheduler.run_pending()
            time.sleep(0.005)
    except KeyboardInterrupt:
        print("\nStopping volume encoder component test...")
    finally:
        input_runtime.stop()


if __name__ == "__main__":
    main()
