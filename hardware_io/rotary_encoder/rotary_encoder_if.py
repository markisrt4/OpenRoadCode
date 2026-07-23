from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


RotationCallback = Callable[[int], None]
ButtonCallback = Callable[[], None]


class RotaryEncoderIf(ABC):
    """
    Interface for receiving rotary encoder events.

    Positive rotation values indicate clockwise movement.
    Negative rotation values indicate counterclockwise movement.
    """

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Return whether the encoder is currently being monitored.

        @retval True Encoder monitoring is active.
        @retval False Encoder monitoring is stopped.
        """

    @abstractmethod
    def start(
        self,
        rotated: RotationCallback,
        button_pressed: ButtonCallback | None = None,
        button_released: ButtonCallback | None = None,
    ) -> None:
        """Start monitoring the rotary encoder.

        @param rotated Callback receiving signed steps since the prior event;
            positive values indicate clockwise rotation.
        @param button_pressed Optional callback invoked on button press.
        @param button_released Optional callback invoked on button release.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        Stop monitoring the rotary encoder.
        """

    def poll(self) -> None:
        """
        Perform implementation-specific polling work.

        Callback-driven encoders may leave this as a no-op. Implementations
        that accumulate hardware events can dispatch them here.
        """
