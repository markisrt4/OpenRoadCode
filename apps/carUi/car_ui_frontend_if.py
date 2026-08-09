"""Application-facing contract for a Car UI frontend implementation."""

from typing import Protocol

from ui.screen_ui_if import ScreenId
from ui.system import StatusUiIf, TopBarUiIf, VolumeUiIf
from ui.ui_action import UiAction
from ui.ui_dispatcher_if import UiDispatcherIf


class CarUiFrontendIf(UiDispatcherIf, Protocol):
    """Shell services required by toolkit-independent Car UI composition."""
    top_bar: TopBarUiIf
    status_bar: StatusUiIf
    volume_panel: VolumeUiIf

    @property
    def empty_value(self) -> str:
        """Return the shell placeholder for an unavailable compact value.

        @return Placeholder text used when compact data is unavailable.
        """
        ...

    def close(self) -> None:
        """Request idempotent frontend shutdown."""
        ...

    def show_main_menu(self) -> None:
        """Navigate to the configured application home menu."""
        ...

    def show_menu(self, menu_key: str) -> None:
        """Display an application menu.

        @param menu_key Stable key identifying the menu to display.
        """
        ...

    def show_screen(self, screen_id: ScreenId) -> None:
        """Navigate to a registered screen destination.

        @param screen_id Stable identifier of the destination screen.
        """
        ...

    def handle_ui_action(self, action: UiAction) -> None:
        """Route one semantic input action through the active UI context.

        @param action Toolkit-independent action to route.
        """
        ...
