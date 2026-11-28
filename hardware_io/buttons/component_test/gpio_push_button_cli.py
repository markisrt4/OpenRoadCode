# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Show press and release events from an active-low GPIO pushbutton."""

import argparse
from threading import Event

from hardware_io.buttons.push_button_callback_if import PushButtonCallbackIf
from hardware_io.gpio import RpiGpioHeader


class PrintButtonEvents(PushButtonCallbackIf):
    def pressed(self) -> None:
        print("PRESSED", flush=True)

    def released(self) -> None:
        print("RELEASED", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pin", type=int, default=11, help="physical header pin (default: 11)")
    args = parser.parse_args()
    try:
        pin = RpiGpioHeader.by_physical_pin(args.pin)
        if not pin.is_gpio:
            raise ValueError(f"Physical pin {args.pin} is not a GPIO pin")
    except ValueError as exc:
        parser.error(str(exc))

    from hardware_io.buttons.rpi_gpio_push_button import RpiGpioPushButton

    print(f"Testing physical pin {pin.physical_pin} (BCM GPIO{pin.bcm}). Ctrl-C to stop.")
    with RpiGpioPushButton(pin, PrintButtonEvents()) as button:
        print(f"Initial state: {button.get_state().name}", flush=True)
        try:
            Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
