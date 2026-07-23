from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import Lock

import RPi.GPIO as GPIO

from hardware_io.gpio import RpiGpioHeader
from hardware_io.rotary_encoder.rotary_encoder_if import (
    ButtonCallback,
    RotaryEncoderIf,
    RotationCallback,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpioRotaryEncoderPins:
    """
    Physical Raspberry Pi header pins used by a rotary encoder.
    """

    pin_a: int
    pin_b: int
    button: int | None = None

    def __post_init__(self) -> None:
        pin_numbers = [
            self.pin_a,
            self.pin_b,
        ]

        if self.button is not None:
            pin_numbers.append(self.button)

        if len(pin_numbers) != len(set(pin_numbers)):
            raise ValueError(
                "Rotary encoder pins must use different physical pins"
            )

        for physical_pin in pin_numbers:
            RpiGpioHeader.bcm_from_physical_pin(physical_pin)


class GpioRotaryEncoder(RotaryEncoderIf):
    """
    Reads a directly connected rotary encoder using Raspberry Pi GPIO.

    Physical Raspberry Pi header pin numbers are used when configuring
    the encoder.
    """

    def __init__(
        self,
        pins: GpioRotaryEncoderPins,
        *,
        button_bounce_ms: int = 200,
        reverse_direction: bool = False,
    ) -> None:
        if button_bounce_ms < 0:
            raise ValueError("button_bounce_ms cannot be negative")

        self._pins = pins
        self._button_bounce_ms = button_bounce_ms
        self._reverse_direction = reverse_direction

        self._bcm_pin_a = RpiGpioHeader.bcm_from_physical_pin(
            pins.pin_a
        )
        self._bcm_pin_b = RpiGpioHeader.bcm_from_physical_pin(
            pins.pin_b
        )

        self._bcm_button = (
            RpiGpioHeader.bcm_from_physical_pin(pins.button)
            if pins.button is not None
            else None
        )

        self._rotated_callback: RotationCallback | None = None
        self._button_pressed_callback: ButtonCallback | None = None
        self._button_released_callback: ButtonCallback | None = None

        self._rotation_count = 0
        self._current_a = GPIO.HIGH
        self._current_b = GPIO.HIGH

        self._lock = Lock()
        self._running = False

    @property
    def pins(self) -> GpioRotaryEncoderPins:
        """Return the GPIO pin assignment used by the encoder.

        @return Immutable A/B/button BCM pin assignment.
        """
        return self._pins

    @property
    def is_running(self) -> bool:
        return self._running

    def start(
        self,
        rotated: RotationCallback,
        button_pressed: ButtonCallback | None = None,
        button_released: ButtonCallback | None = None,
    ) -> None:
        if not callable(rotated):
            raise TypeError("rotated must be callable")

        if button_pressed is not None and not callable(button_pressed):
            raise TypeError("button_pressed must be callable")

        if button_released is not None and not callable(button_released):
            raise TypeError("button_released must be callable")

        if self._running:
            return

        self._rotated_callback = rotated
        self._button_pressed_callback = button_pressed
        self._button_released_callback = button_released

        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(
            self._bcm_pin_a,
            GPIO.IN,
            pull_up_down=GPIO.PUD_UP,
        )
        GPIO.setup(
            self._bcm_pin_b,
            GPIO.IN,
            pull_up_down=GPIO.PUD_UP,
        )

        self._current_a = GPIO.input(self._bcm_pin_a)
        self._current_b = GPIO.input(self._bcm_pin_b)

        GPIO.add_event_detect(
            self._bcm_pin_a,
            GPIO.BOTH,
            callback=self._rotary_interrupt,
        )

        GPIO.add_event_detect(
            self._bcm_pin_b,
            GPIO.BOTH,
            callback=self._rotary_interrupt,
        )

        if self._bcm_button is not None:
            GPIO.setup(
                self._bcm_button,
                GPIO.IN,
                pull_up_down=GPIO.PUD_UP,
            )

            GPIO.add_event_detect(
                self._bcm_button,
                GPIO.BOTH,
                callback=self._button_interrupt,
                bouncetime=self._button_bounce_ms,
            )

        self._running = True

        LOGGER.info(
            "GPIO rotary encoder started using physical pins %s",
            self._pins,
        )

    def stop(self) -> None:
        if not self._running:
            return

        GPIO.remove_event_detect(self._bcm_pin_a)
        GPIO.remove_event_detect(self._bcm_pin_b)

        if self._bcm_button is not None:
            GPIO.remove_event_detect(self._bcm_button)

        self._running = False

        self._rotated_callback = None
        self._button_pressed_callback = None
        self._button_released_callback = None

        LOGGER.info(
            "GPIO rotary encoder stopped using physical pins %s",
            self._pins,
        )

    def cleanup(self) -> None:
        """
        Stop monitoring and release only the GPIO channels used by this
        encoder.
        """
        self.stop()

        channels = [
            self._bcm_pin_a,
            self._bcm_pin_b,
        ]

        if self._bcm_button is not None:
            channels.append(self._bcm_button)

        GPIO.cleanup(channels)

    def poll(self) -> None:
        """
        Dispatch accumulated rotary movement.

        This method should be called periodically by the component using the
        encoder.
        """
        with self._lock:
            steps = self._rotation_count
            self._rotation_count = 0

        if steps == 0:
            return

        if self._reverse_direction:
            steps = -steps

        callback = self._rotated_callback

        if callback is None:
            return

        try:
            callback(steps)
        except Exception:
            LOGGER.exception("GPIO rotary encoder callback failed")

    def tick(self) -> None:
        """Backward-compatible alias for poll()."""
        self.poll()

    def _rotary_interrupt(self, channel: int) -> None:
        current_a = GPIO.input(self._bcm_pin_a)
        current_b = GPIO.input(self._bcm_pin_b)

        if (
            current_a == self._current_a
            and current_b == self._current_b
        ):
            return

        self._current_a = current_a
        self._current_b = current_b

        if current_a == GPIO.HIGH and current_b == GPIO.HIGH:
            with self._lock:
                if channel == self._bcm_pin_a:
                    self._rotation_count += 1
                else:
                    self._rotation_count -= 1

    def _button_interrupt(self, _channel: int) -> None:
        if self._bcm_button is None:
            return

        pressed = GPIO.input(self._bcm_button) == GPIO.LOW

        callback = (
            self._button_pressed_callback
            if pressed
            else self._button_released_callback
        )

        if callback is None:
            return

        try:
            callback()
        except Exception:
            LOGGER.exception(
                "GPIO rotary encoder button callback failed"
            )

    def __enter__(self) -> GpioRotaryEncoder:
        if self._rotated_callback is None:
            raise RuntimeError(
                "Callbacks must be configured through start() before "
                "using the encoder as a context manager"
            )

        self.start(
            rotated=self._rotated_callback,
            button_pressed=self._button_pressed_callback,
            button_released=self._button_released_callback,
        )

        return self

    def __exit__(self, *_args: object) -> None:
        self.cleanup()
