#!/usr/bin/env python3

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from pathlib import Path

from apps.carUi.config.car_ui_runtime_config_parser import (
    CarUiRuntimeConfigParser,
    RotaryEncoderConfig,
)
from apps.carUi.input import EncoderEventRouter
from apps.carUi.runtime.rotary_encoder_runtime import (
    create_rotary_encoder_runtime,
)
from controllers.audio import PipewireAudioController


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT
    / "apps"
    / "carUi"
    / "config"
    / "car_ui_runtime.toml"
)
DEFAULT_VOLUME_STEPS = 20


class CliScheduler:
    """Small Tk-compatible scheduler used to drive the event router."""

    def __init__(self) -> None:
        self._next_id = 0
        self._callbacks: dict[
            str,
            tuple[float, Callable[[], None]],
        ] = {}

    def after(
        self,
        delay_ms: int,
        callback: Callable[[], None],
    ) -> str:
        self._next_id += 1
        callback_id = f"after-{self._next_id}"
        deadline = time.monotonic() + (delay_ms / 1000)
        self._callbacks[callback_id] = (deadline, callback)
        return callback_id

    def after_cancel(self, callback_id: str) -> None:
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
    config = CarUiRuntimeConfigParser(
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

    router = EncoderEventRouter(
        root=scheduler,
        encoders=encoder_runtime.encoders,
        volume_encoder_index=encoder_runtime.volume_index,
        volume_up=volume_up,
        volume_down=volume_down,
        volume_button_pressed=toggle_mute,
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

    router.start()

    try:
        while True:
            scheduler.run_pending()
            time.sleep(0.005)
    except KeyboardInterrupt:
        print("\nStopping volume encoder component test...")
    finally:
        router.stop()


if __name__ == "__main__":
    main()
