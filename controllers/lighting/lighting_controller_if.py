from __future__ import annotations

from concurrent.futures import Future
from typing import Protocol, runtime_checkable

from controllers.lighting.lighting_types import (
    CustomPatternMode,
    LightingState,
    RgbColor,
)


@runtime_checkable
class LightingControllerIf(Protocol):
    """Thread-friendly controller contract for lighting applications."""

    @property
    def is_connected(self) -> bool:
        """Return whether the controller is connected to its lighting device.

        @retval True The device connection is active.
        @retval False The device is disconnected.
        """
        ...

    def current_state(self) -> LightingState:
        """Return the most recently requested lighting state.

        @return Immutable snapshot of connection and lighting settings.
        """
        ...

    def connect(self) -> Future[None]:
        """Begin connecting to the lighting device.

        @return Future completed when the device is ready, or completed with
            the connection exception.
        """
        ...

    def disconnect(self) -> Future[None]:
        """Begin disconnecting from the lighting device.

        @return Future completed when disconnection finishes, or completed
            with the disconnection exception.
        """
        ...

    def close(self) -> None:
        """Release controller resources and prevent further operations."""
        ...

    def set_power(self, enabled: bool) -> Future[None]:
        """Set lighting power.

        @param enabled ``True`` to turn the lights on.
        @return Future completed when the command has been processed.
        """
        ...

    def set_color(self, color: RgbColor) -> Future[None]:
        """Set the static RGB color.

        @param color Red, green, and blue channel values.
        @return Future completed when the command has been processed.
        """
        ...

    def set_brightness(self, percent: int) -> Future[None]:
        """Set brightness as a percentage.

        @param percent Brightness in the inclusive range 0 through 100.
        @return Future completed when the command has been processed.
        """
        ...

    def set_color_temperature(self, percent: int) -> Future[None]:
        """Set the warm-to-cool white balance.

        @param percent Color temperature percentage accepted by the device.
        @return Future completed when the command has been processed.
        """
        ...

    def set_pattern(self, pattern_index: int) -> Future[None]:
        """Select a built-in lighting pattern.

        @param pattern_index Device-specific pattern index.
        @return Future completed when the command has been processed.
        """
        ...

    def set_music_mode(self, eq_mode: int) -> Future[None]:
        """Select a sound-reactive equalizer mode.

        @param eq_mode Device-specific equalizer mode.
        @return Future completed when the command has been processed.
        """
        ...

    def set_custom_pattern_mode(
        self,
        mode: CustomPatternMode,
    ) -> Future[None]:
        """Set the animation mode for a custom pattern.

        @param mode Custom animation mode.
        @return Future completed when the command has been processed.
        """
        ...

    def set_custom_pattern_direction(
        self,
        is_forward: bool,
    ) -> Future[None]:
        """Set the animation direction for a custom pattern.

        @param is_forward ``True`` for forward animation.
        @return Future completed when the command has been processed.
        """
        ...
