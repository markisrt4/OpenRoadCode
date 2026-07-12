from __future__ import annotations

from hardware_io.gpio.gpio_pin import GpioPin


class RpiGpioHeader:
    """
    Raspberry Pi 40-pin GPIO header mapping.

    Physical header pin numbers are used as the primary key.
    """

    _pins: dict[int, GpioPin] = {
        1: GpioPin(1, None, "3V3", "Power"),
        2: GpioPin(2, None, "5V", "Power"),
        3: GpioPin(3, 2, "GPIO2", "I2C1 SDA"),
        4: GpioPin(4, None, "5V", "Power"),
        5: GpioPin(5, 3, "GPIO3", "I2C1 SCL"),
        6: GpioPin(6, None, "GND", "Ground"),
        7: GpioPin(7, 4, "GPIO4", "GPCLK0"),
        8: GpioPin(8, 14, "GPIO14", "UART0 TXD"),
        9: GpioPin(9, None, "GND", "Ground"),
        10: GpioPin(10, 15, "GPIO15", "UART0 RXD"),
        11: GpioPin(11, 17, "GPIO17", "GPIO"),
        12: GpioPin(12, 18, "GPIO18", "PWM0"),
        13: GpioPin(13, 27, "GPIO27", "GPIO"),
        14: GpioPin(14, None, "GND", "Ground"),
        15: GpioPin(15, 22, "GPIO22", "GPIO"),
        16: GpioPin(16, 23, "GPIO23", "GPIO"),
        17: GpioPin(17, None, "3V3", "Power"),
        18: GpioPin(18, 24, "GPIO24", "GPIO"),
        19: GpioPin(19, 10, "GPIO10", "SPI0 MOSI"),
        20: GpioPin(20, None, "GND", "Ground"),
        21: GpioPin(21, 9, "GPIO9", "SPI0 MISO"),
        22: GpioPin(22, 25, "GPIO25", "GPIO"),
        23: GpioPin(23, 11, "GPIO11", "SPI0 SCLK"),
        24: GpioPin(24, 8, "GPIO8", "SPI0 CE0"),
        25: GpioPin(25, None, "GND", "Ground"),
        26: GpioPin(26, 7, "GPIO7", "SPI0 CE1"),
        27: GpioPin(27, 0, "GPIO0", "ID_SD"),
        28: GpioPin(28, 1, "GPIO1", "ID_SC"),
        29: GpioPin(29, 5, "GPIO5", "GPIO"),
        30: GpioPin(30, None, "GND", "Ground"),
        31: GpioPin(31, 6, "GPIO6", "GPIO"),
        32: GpioPin(32, 12, "GPIO12", "PWM0"),
        33: GpioPin(33, 13, "GPIO13", "PWM1"),
        34: GpioPin(34, None, "GND", "Ground"),
        35: GpioPin(35, 19, "GPIO19", "PWM1"),
        36: GpioPin(36, 16, "GPIO16", "GPIO"),
        37: GpioPin(37, 26, "GPIO26", "GPIO"),
        38: GpioPin(38, 20, "GPIO20", "GPIO"),
        39: GpioPin(39, None, "GND", "Ground"),
        40: GpioPin(40, 21, "GPIO21", "GPIO"),
    }

    _bcm_lookup: dict[int, GpioPin] = {
        pin.bcm: pin
        for pin in _pins.values()
        if pin.bcm is not None
    }

    @classmethod
    def by_physical_pin(cls, physical_pin: int) -> GpioPin:
        """
        Return pin information by physical header pin number.
        """
        try:
            return cls._pins[physical_pin]
        except KeyError as exc:
            raise ValueError(
                f"Invalid physical pin: {physical_pin}"
            ) from exc

    @classmethod
    def by_bcm(cls, bcm: int) -> GpioPin:
        """
        Return pin information by BCM GPIO number.
        """
        try:
            return cls._bcm_lookup[bcm]
        except KeyError as exc:
            raise ValueError(
                f"Invalid BCM GPIO: {bcm}"
            ) from exc

    @classmethod
    def bcm_from_physical_pin(cls, physical_pin: int) -> int:
        """
        Convert a physical header pin number to a BCM GPIO number.
        """
        pin = cls.by_physical_pin(physical_pin)

        if pin.bcm is None:
            raise ValueError(
                f"Physical pin {physical_pin} "
                f"({pin.name}) is not a GPIO pin"
            )

        return pin.bcm

    @classmethod
    def physical_pin_from_bcm(cls, bcm: int) -> int:
        """
        Convert a BCM GPIO number to a physical header pin number.
        """
        return cls.by_bcm(bcm).physical_pin

    @classmethod
    def is_gpio_pin(cls, physical_pin: int) -> bool:
        """
        Return whether a physical header pin is a GPIO pin.
        """
        return cls.by_physical_pin(physical_pin).is_gpio

    @classmethod
    def all_pins(cls) -> list[GpioPin]:
        """
        Return all header pins.
        """
        return list(cls._pins.values())

    @classmethod
    def all_gpio_pins(cls) -> list[GpioPin]:
        """
        Return only pins with BCM GPIO numbers.
        """
        return [
            pin
            for pin in cls._pins.values()
            if pin.is_gpio
        ]
