"""Concrete no-op top-bar UI implementation."""

from collections.abc import Callable

from ui.system.top_bar_ui_if import TopBarUiIf


class TopBarUiStub(TopBarUiIf):
    """Ignore top-bar updates and navigation actions."""

    def set_title(self, title: str) -> None:
        pass

    def set_back_action(self, action: Callable[[], None]) -> None:
        pass

    def show_back_button(self, text: str | None = None) -> None:
        pass

    def hide_back_button(self) -> None:
        pass

    def invoke_back_action(self) -> None:
        pass

    def set_frequency_text(self, text: str) -> None:
        pass

    def set_location_text(self, text: str) -> None:
        pass
