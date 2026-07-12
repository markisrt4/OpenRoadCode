#!/usr/bin/env python3

from hardware_io.gpio import RpiGpioHeader


def main() -> None:
    print(f"{'PIN':>4} {'BCM':>4} {'NAME':<8} FUNCTION")

    for pin in RpiGpioHeader.all_pins():
        bcm = "-" if pin.bcm is None else str(pin.bcm)

        print(
            f"{pin.physical_pin:>4} "
            f"{bcm:>4} "
            f"{pin.name:<8} "
            f"{pin.function}"
        )


if __name__ == "__main__":
    main()
