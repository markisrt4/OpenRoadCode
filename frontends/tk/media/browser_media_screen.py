# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Screen adapters for browser-backed media panels."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable
from typing import Protocol

from frontends.tk.media.spotify_services_if import BrowserMediaPlayerIf
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId

MediaNavigationFactory = Callable[[tk.Misc, str], tk.Widget]


class BrowserMediaPanelIf(Protocol):
    """Panel contract needed by a browser-backed media screen."""

    def pack(self, *args, **kwargs) -> None:
        """Place the panel in the Tk layout."""
        ...

    def open_home(self) -> None:
        """Launch the provider's default kiosk destination."""
        ...


BrowserMediaPanelFactory = Callable[
    [
        tk.Misc,
        BrowserMediaPlayerIf,
        str,
        Callable[[str], None],
        Callable[[], None],
    ],
    BrowserMediaPanelIf,
]


class BrowserMediaScreen(TkScreen):
    """Adapt a browser media panel to the shared screen lifecycle."""

    def __init__(
        self,
        screen_id: str,
        host: TkScreenHostIf,
        *,
        title: str,
        player: BrowserMediaPlayerIf,
        panel_factory: BrowserMediaPanelFactory,
        back_action: Callable[[], None],
        media_navigation_factory: MediaNavigationFactory | None = None,
    ) -> None:
        super().__init__(ScreenId(screen_id))
        self._host = host
        self._title = title
        self._player = player
        self._panel_factory = panel_factory
        self._back_action = back_action
        self._media_navigation_factory = media_navigation_factory

    def show(self) -> None:
        """Open the provider directly while retaining ORC media navigation."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title(self._title)
        self._host.set_screen_back_action(self._back_action)

        root = tk.Frame(self._host.screen_parent)
        root.pack(fill=tk.BOTH, expand=True)

        if self._media_navigation_factory is not None:
            self._media_navigation_factory(
                root,
                self.screen_id.value,
            ).pack(fill=tk.X, padx=4, pady=(4, 2))

        panel = self._panel_factory(
            root,
            self._player,
            os.environ.get("DISPLAY", ":1"),
            self._host.set_screen_status,
            self._back_action,
        )
        panel.pack(fill=tk.BOTH, expand=True)

        # The browser uses the panel's final screen coordinates for kiosk
        # placement. Resolve Tk geometry first, then launch immediately so the
        # user never lands on a redundant provider-specific launch screen.
        root.update_idletasks()
        panel.open_home()

    def hide(self) -> None:
        """Stop the browser owned by this screen when navigating away."""
        self._player.stop()
