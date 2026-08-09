"""Toolkit-independent contract for a navigable UI screen."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ui.ui_action import UiAction


@dataclass(frozen=True, slots=True)
class ScreenId:
    """Stable identifier for a navigable screen.

    @param value Non-empty identifier value; surrounding whitespace is removed.
    """

    value: str

    def __post_init__(self) -> None:
        normalized_value = self.value.strip()
        if not normalized_value:
            raise ValueError("Screen identifier must not be empty")
        object.__setattr__(self, "value", normalized_value)

    def __str__(self) -> str:
        return self.value


class ScreenUiIf(ABC):
    """Lifecycle and action contract for one navigable screen.

    Implementations may use any UI toolkit. A screen is a navigation
    destination and may compose any number of toolkit-specific panels and
    widgets.
    """

    @property
    @abstractmethod
    def screen_id(self) -> ScreenId:
        """Return the stable identifier used to navigate to this screen.

        @return Stable screen identifier.
        """
        ...

    @abstractmethod
    def show(self) -> None:
        """Make the screen active and ready to receive UI actions."""
        ...

    @abstractmethod
    def hide(self) -> None:
        """Make the screen inactive and release transient activity."""
        ...

    @abstractmethod
    def handle_ui_action(self, action: UiAction) -> bool:
        """Handle a semantic action offered to the active screen.

        @param action Semantic UI action offered to the screen.
        @return True when handled; False when the parent should handle it.
        """
        ...
