# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Physical component test for KeyboardInputAdapter."""

from __future__ import annotations

import argparse
import sys
import time

from input_events import InputDeviceId, InputDeviceType
from controllers.input.input_manager import InputManager
from controllers.input.input_mapper import InputMapper
from controllers.input.keyboard_input_adapter import KeyboardInputAdapter
from hardware_io.keyboard.keyboard_reader import KeyboardReader
from ui.ui_action import UiAction
from ui.ui_event_handler_if import UiEventHandlerIf


class PrintingUiEventHandler(UiEventHandlerIf):
    """Print every mapped UI action."""

    def handle_ui_action(
        self,
        action: UiAction,
    ) -> None:
        print(f"UI action: {action.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test physical keyboard input mapping"
    )

    parser.add_argument(
        "--device",
        help="Linux input device path, such as /dev/input/event3",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    keyboard_id = InputDeviceId(
        device_type=InputDeviceType.KEYBOARD,
        instance=0,
    )

    user_encoder_id = InputDeviceId(
        device_type=InputDeviceType.ROTARY_ENCODER,
        instance=0,
    )

    volume_encoder_id = InputDeviceId(
        device_type=InputDeviceType.ROTARY_ENCODER,
        instance=1,
    )

    input_manager = InputManager(
        mapper=InputMapper(
            user_encoder_id=user_encoder_id,
            volume_encoder_id=volume_encoder_id,
        ),
        ui_handler=PrintingUiEventHandler(),
    )

    adapter = KeyboardInputAdapter(
        keyboard=KeyboardReader(device_path=args.device),
        device_id=keyboard_id,
        input_handler=input_manager,
    )

    try:
        adapter.connect()
    except (FileNotFoundError, PermissionError, RuntimeError, OSError) as exc:
        print(f"Unable to open a keyboard input device: {exc}", file=sys.stderr)
        print(
            "This test requires a Linux /dev/input/event* device. "
            "If running in a VM, enable input-device or USB passthrough; "
            "otherwise pass one explicitly with --device.",
            file=sys.stderr,
        )
        print(
            "For a hardware-free test, run: "
            "python3 -m "
            "controllers.input.component_test.mock_input_adapters_cli",
            file=sys.stderr,
        )
        return 2

    print("Keyboard adapter connected.")
    print("Press mapped keys to display UI actions.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print()
        print("Stopping keyboard adapter...")
    finally:
        adapter.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
