# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Screen adapters for browser-backed media panels."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable

from frontends.tk.media.spotify_services_if import BrowserMediaPlayerIf
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId


class BrowserMediaScreen(TkScreen):
    """Adapt a browser media panel to the shared screen lifecycle."""

    def __init__(
        self,
        screen_id: str,
        host: TkScreenHostIf,
        *,
        title: str,
        player: BrowserMediaPlayerIf,
        panel_factory: Callable[[tk.Misc, BrowserMediaPlayerIf, str, Callable[[str], None], Callable[[], None]], tk.Widget],
        back_action: Callable[[], None],
    ) -> None:
        super().__init__(ScreenId(screen_id))
        self._host = host
        self._title = title
        self._player = player
        self._panel_factory = panel_factory
        self._back_action = back_action

    def show(self) -> None:
        """Build the panel and make it the active ORC screen."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title(self._title)
        self._host.set_screen_back_action(self._back_action)
        self._panel_factory(
            self._host.screen_parent,
            self._player,
            os.environ.get("DISPLAY", ":1"),
            self._host.set_screen_status,
            self._back_action,
        ).pack(fill=tk.BOTH, expand=True)

    def hide(self) -> None:
        """Stop the browser owned by this screen when navigating away."""
        self._player.stop()
