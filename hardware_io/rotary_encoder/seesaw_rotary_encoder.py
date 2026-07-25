from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from time import sleep
from typing import Any

import board
from adafruit_seesaw import digitalio, rotaryio, seesaw

from hardware_io.rotary_encoder.rotary_encoder_if import (
    ButtonCallback,
    RotaryEncoderIf,
    RotationCallback,
)


LOGGER = logging.getLogger(__name__)

ENCODER_POSITION_HALF_RANGE = 1 << 31


class SeesawRotaryEncoder(RotaryEncoderIf):
    """
    Reads rotary encoder events from an Adafruit Seesaw I2C device.

    Rotation and button events are monitored in a background thread.
    """

    DEFAULT_ADDRESS = 0x36
    DEFAULT_BUTTON_PIN = 24
    DEFAULT_POLL_INTERVAL = 0.01

    def __init__(
        self,
        address: int = DEFAULT_ADDRESS,
        *,
        i2c: Any | None = None,
        button_pin: int = DEFAULT_BUTTON_PIN,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        reverse_direction: bool = False,
        debounce_seconds: float = 0.03,
    ) -> None:
        """
        Args:
            address:
                I2C address of the Seesaw device.

            i2c:
                Optional initialized I2C bus. When omitted, board.I2C() is used.

            button_pin:
                Seesaw GPIO pin connected to the encoder button.

            poll_interval:
                Delay between hardware reads, in seconds.

            reverse_direction:
                Reverse the reported rotation direction.

            debounce_seconds:
                Time that the button state must remain stable before a button
                event is emitted.
        """
        if not 0 <= address <= 0x7F:
            raise ValueError("address must be a valid 7-bit I2C address")

        if poll_interval <= 0:
            raise ValueError("poll_interval must be greater than zero")

        if debounce_seconds < 0:
            raise ValueError("debounce_seconds cannot be negative")

        self._address = address
        self._i2c = i2c
        self._button_pin = button_pin
        self._poll_interval = poll_interval
        self._reverse_direction = reverse_direction
        self._debounce_seconds = debounce_seconds

        self._seesaw: seesaw.Seesaw | None = None
        self._encoder: rotaryio.IncrementalEncoder | None = None
        self._button: digitalio.DigitalIO | None = None

        self._rotated_callback: RotationCallback | None = None
        self._button_pressed_callback: ButtonCallback | None = None
        self._button_released_callback: ButtonCallback | None = None

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def address(self) -> int:
        return self._address

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

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

        if self.is_running:
            return

        self._rotated_callback = rotated
        self._button_pressed_callback = button_pressed
        self._button_released_callback = button_released

        self._open()

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"SeesawRotaryEncoder-{self._address:#04x}",
            daemon=True,
        )
        self._thread.start()

        LOGGER.info(
            "Seesaw rotary encoder started at address %#04x",
            self._address,
        )

    def stop(self) -> None:
        self._stop_event.set()

        if (
            self._thread is not None
            and self._thread.is_alive()
            and self._thread is not threading.current_thread()
        ):
            self._thread.join(timeout=1.0)

        self._thread = None

        self._rotated_callback = None
        self._button_pressed_callback = None
        self._button_released_callback = None

        LOGGER.info(
            "Seesaw rotary encoder stopped at address %#04x",
            self._address,
        )

    def _open(self) -> None:
        if self._seesaw is not None:
            return

        if self._i2c is None:
            self._i2c = board.I2C()

        self._seesaw = seesaw.Seesaw(
            self._i2c,
            addr=self._address,
        )

        self._encoder = rotaryio.IncrementalEncoder(self._seesaw)
        self._encoder.position = 0
        self._seesaw.encoder_delta()

        self._seesaw.pin_mode(
            self._button_pin,
            self._seesaw.INPUT_PULLUP,
        )

        self._button = digitalio.DigitalIO(
            self._seesaw,
            self._button_pin,
        )

    def _run(self) -> None:
        if self._seesaw is None or self._button is None:
            raise RuntimeError("Rotary encoder is not initialized")

        stable_button_state = self._read_button_pressed()
        pending_button_state = stable_button_state
        pending_button_time = 0.0

        try:
            while not self._stop_event.is_set():
                steps = self._read_rotation_steps()

                if steps != 0:
                    if self._reverse_direction:
                        steps = -steps

                    self._call_rotation_callback(steps)

                current_button_state = self._read_button_pressed()

                if current_button_state != pending_button_state:
                    pending_button_state = current_button_state
                    pending_button_time = 0.0

                elif current_button_state != stable_button_state:
                    pending_button_time += self._poll_interval

                    if pending_button_time >= self._debounce_seconds:
                        stable_button_state = current_button_state
                        self._call_button_callback(stable_button_state)

                sleep(self._poll_interval)

        except Exception:
            if not self._stop_event.is_set():
                LOGGER.exception(
                    "Seesaw rotary encoder failed at address %#04x",
                    self._address,
                )

    def _read_rotation_steps(self) -> int:
        if self._seesaw is None:
            raise RuntimeError("Rotary encoder is not initialized")

        steps = self._seesaw.encoder_delta()

        if steps == -ENCODER_POSITION_HALF_RANGE:
            LOGGER.debug(
                "Ignoring invalid encoder delta at address %#04x",
                self._address,
            )
            return 0

        return steps

    def _read_button_pressed(self) -> bool:
        if self._button is None:
            raise RuntimeError("Rotary encoder button is not initialized")

        return not self._button.value

    def _call_rotation_callback(self, steps: int) -> None:
        callback = self._rotated_callback

        if callback is None:
            return

        try:
            callback(steps)
        except Exception:
            LOGGER.exception(
                "Rotation callback failed at address %#04x",
                self._address,
            )

    def _call_button_callback(self, pressed: bool) -> None:
        callback: Callable[[], None] | None

        if pressed:
            callback = self._button_pressed_callback
        else:
            callback = self._button_released_callback

        if callback is None:
            return

        try:
            callback()
        except Exception:
            LOGGER.exception(
                "Button callback failed at address %#04x",
                self._address,
            )
