"""Raspberry Pi GPIO pushbutton implementation."""

from __future__ import annotations

from threading import Lock

from gpiozero import Button

from hardware_io.buttons.push_button_callback_if import PushButtonCallbackIf
from hardware_io.buttons.push_button_if import PushButtonIf
from hardware_io.buttons.push_button_state import PushButtonState
from hardware_io.gpio.gpio_pin import GpioPin


class RpiGpioPushButton(PushButtonIf):
    """Pushbutton connected to a Raspberry Pi GPIO input.

    The supplied GpioPin describes both the physical header position and
    corresponding BCM GPIO number.

    In the typical active-low configuration, one switch terminal is
    connected to the GPIO pin and the other terminal is connected to
    ground. The Raspberry Pi's internal pull-up resistor is then used.
    """

    def __init__(
        self,
        gpio_pin: GpioPin,
        callback: PushButtonCallbackIf | None = None,
        *,
        active_low: bool = True,
        debounce_seconds: float = 0.05,
    ) -> None:
        """Initialize the GPIO pushbutton.

        Args:
            gpio_pin: Raspberry Pi GPIO header pin description.
            callback: Optional receiver for pressed and released events.
            active_low: True when pressing the button connects GPIO to ground.
            debounce_seconds: Time during which repeated transitions are ignored.

        Raises:
            ValueError: If gpio_pin does not describe a GPIO-capable pin.
            ValueError: If debounce_seconds is negative.
        """
        if not gpio_pin.is_gpio:
            raise ValueError(
                f"Physical pin {gpio_pin.physical_pin} "
                f"({gpio_pin.name}) is not a GPIO pin"
            )

        if debounce_seconds < 0:
            raise ValueError("debounce_seconds must be non-negative")

        self._gpio_pin = gpio_pin
        self._callback = callback
        self._active_low = active_low
        self._debounce_seconds = debounce_seconds

        self._button: Button | None = None
        self._lock = Lock()

    @property
    def gpio_pin(self) -> GpioPin:
        """Return the GPIO pin used by this pushbutton."""
        return self._gpio_pin

    def start(self) -> None:
        """Configure the GPIO input and begin monitoring button events."""
        with self._lock:
            if self._button is not None:
                return

            bcm_pin = self._gpio_pin.bcm

            if bcm_pin is None:
                # Protected by constructor validation, but keeps type checking
                # and future modifications honest.
                raise RuntimeError(
                    f"Pin {self._gpio_pin.physical_pin} has no BCM mapping"
                )

            self._button = Button(
                pin=bcm_pin,
                pull_up=self._active_low,
                bounce_time=self._debounce_seconds,
            )

            self._button.when_pressed = self._handle_pressed
            self._button.when_released = self._handle_released

    def stop(self) -> None:
        """Stop monitoring and release the GPIO resource."""
        with self._lock:
            button = self._button
            self._button = None

        if button is None:
            return

        button.when_pressed = None
        button.when_released = None
        button.close()

    def get_state(self) -> PushButtonState:
        """Return the current physical state of the pushbutton.

        Raises:
            RuntimeError: If monitoring has not been started.
        """
        with self._lock:
            button = self._button

        if button is None:
            raise RuntimeError("Pushbutton has not been started")

        if button.is_pressed:
            return PushButtonState.PRESSED

        return PushButtonState.RELEASED

    def set_callback(
        self,
        callback: PushButtonCallbackIf | None,
    ) -> None:
        """Set or clear the callback receiver."""
        with self._lock:
            self._callback = callback

    def _handle_pressed(self) -> None:
        """Forward a pressed event to the configured callback."""
        with self._lock:
            callback = self._callback

        if callback is not None:
            callback.pressed()

    def _handle_released(self) -> None:
        """Forward a released event to the configured callback."""
        with self._lock:
            callback = self._callback

        if callback is not None:
            callback.released()

    def __enter__(self) -> RpiGpioPushButton:
        """Start monitoring when entering a context."""
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        """Stop monitoring when leaving a context."""
        self.stop()
