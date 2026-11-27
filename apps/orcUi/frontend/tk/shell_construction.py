# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Construct shell widgets independently of the application's lifecycle owner."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .shell_view import OrcUiShellView

if TYPE_CHECKING:
    from .orc_ui_app import OrcUiApp


def build_shell(app: OrcUiApp, factory: type[OrcUiShellView]) -> None:
    if app._power_dialog is None:
        raise RuntimeError("Power dialog must be initialized before shell construction")
    app._shell = factory(
        app._root,
        theme=app._theme,
        theme_mode=app._theme_mode,
        nav_items=app._nav_items,
        active_nav=app._active_nav,
        on_navigate=app._navigate_from_sidebar,
        on_power=app._power_dialog.show,
        on_online_toggle=app._toggle_online_mode,
        on_theme_toggle=app._toggle_theme,
        on_settings=app._open_settings,
        on_volume_down=app._request_volume_down,
        on_volume_up=app._request_volume_up,
        volume_text=app._volume_text(),
    )
    app._content = app._shell.content
    if app.online_mode is not None:
        app.set_online_status(app.online_mode.online, app._internet_status)



def format_volume(percent: float | None, muted: bool) -> str:
    """Format the shell's retained volume readout."""
    icon = "🔇" if muted else "🔊"
    return f"{icon} --" if percent is None else f"{icon} {round(percent)}%"
