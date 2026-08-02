from abc import ABC, abstractmethod
import tkinter as tk
from collections.abc import Callable
from typing import Any

from apps.carUi.input import PanelEncoderCallbacks


class PanelManagerIf(ABC):
    """Base contract and shared helpers for Car UI panel managers."""

    def __init__(self, app: Any) -> None:
        self.app = app

    @abstractmethod
    def show(self) -> None:
        """Display the panel and configure its input callbacks."""

    def prepare_panel(self, title: str) -> bool:
        """Reset shared UI state before displaying a panel.

        @param title Title to show in the application's top bar.
        @return Always ``True`` for use in guard-style panel setup.
        """
        self.clear_encoder_callbacks()

        navigation = getattr(self.app, "navigation", None)
        if navigation is not None:
            navigation.clear_content()
        else:
            self.app._clear_content()

        self.set_title(title)
        self.app.top_bar.show_back_button()
        return True

    def set_encoder_callbacks(
        self,
        *,
        rotated: Callable[[int, int], None] | None = None,
        button_pressed: Callable[[int], None] | None = None,
        button_released: Callable[[int], None] | None = None,
    ) -> None:
        """
        Route non-volume encoder events to this panel while it is displayed.

        Rotation callbacks receive the contextual encoder slot and signed step
        count. Button callbacks receive the contextual encoder slot.

        @param rotated Optional rotation callback.
        @param button_pressed Optional encoder-button press callback.
        @param button_released Optional encoder-button release callback.
        """
        setter = getattr(self.app, "set_panel_encoder_callbacks", None)
        if setter is None:
            return

        setter(
            PanelEncoderCallbacks(
                rotated=rotated,
                button_pressed=button_pressed,
                button_released=button_released,
            )
        )

    def clear_encoder_callbacks(self) -> None:
        """Remove callbacks installed for the currently displayed panel."""
        clear = getattr(self.app, "clear_panel_encoder_callbacks", None)
        if clear is not None:
            clear()

    def set_title(self, title: str) -> None:
        """Set the panel title.

        @param title User-visible title text.
        """
        if hasattr(self.app, "set_panel_title"):
            self.app.set_panel_title(title)
        else:
            self.app.top_bar.set_title(title)

    def set_status(self, message: str) -> None:
        """Set the panel's user-visible status message.

        @param message Status text to display.
        """
        status_bar = getattr(self.app, "status_bar", None)
        if status_bar is not None:
            status_bar.set_status(message)
        else:
            self.app.status_var.set(message)

    @property
    def content_frame(self) -> tk.Frame:
        """Return the shared frame into which panel content is rendered.

        @return Tk frame owned by the application content area.
        """
        return self.app.content_frame

    @property
    def remote_display(self) -> str:
        """Return the display identifier used for launched applications.

        @return X display string such as ``":2"``.
        """
        return self.app.remote_display

    def create_tile(
        self,
        parent: tk.Widget,
        key: str,
        label: str,
        subtitle: str,
        detail: str,
    ) -> tk.Frame:
        """Create a standard navigation tile.

        @param parent Widget that owns the tile.
        @param key Stable navigation key for the tile.
        @param label Primary user-visible label.
        @param subtitle Secondary user-visible label.
        @param detail Additional descriptive text.
        @return Frame containing the configured tile.
        """
        return self.app.create_subpanel_tile(parent, key, label, subtitle, detail)
