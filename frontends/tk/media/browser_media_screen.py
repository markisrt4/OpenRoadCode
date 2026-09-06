# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Screen adapter for browser-backed media destinations."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable

from frontends.tk.media.spotify_services_if import BrowserMediaPlayerIf
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from frontends.x11 import X11WindowEmbedder
from ui.screen_ui_if import ScreenId

MediaNavigationFactory = Callable[[tk.Misc, str], tk.Widget]


class BrowserMediaScreen(TkScreen):
    """Launch and reparent one managed browser directly into an ORC screen."""

    def __init__(
        self,
        screen_id: str,
        host: TkScreenHostIf,
        *,
        title: str,
        player: BrowserMediaPlayerIf,
        default_target: str,
        window_class: str,
        back_action: Callable[[], None],
        media_navigation_factory: MediaNavigationFactory | None = None,
    ) -> None:
        super().__init__(ScreenId(screen_id))
        self._host = host
        self._title = title
        self._player = player
        self._default_target = default_target
        self._window_class = window_class
        self._back_action = back_action
        self._media_navigation_factory = media_navigation_factory
        self._launch_job: object | None = None
        self._embedder = X11WindowEmbedder()
        self._browser_host: tk.Frame | None = None

    def show(self) -> None:
        """Show media navigation and launch the provider directly below it."""
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title(self._title)
        self._host.set_screen_back_action(self._back_action)

        root = tk.Frame(self._host.screen_parent, bg="#000000")
        root.pack(fill=tk.BOTH, expand=True)

        if self._media_navigation_factory is not None:
            self._media_navigation_factory(
                root,
                self.screen_id.value,
            ).pack(fill=tk.X, padx=4, pady=(4, 2))

        browser_host = tk.Frame(root, bg="#000000")
        browser_host.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))
        browser_host.bind("<Configure>", self._on_browser_host_resize)
        self._browser_host = browser_host

        # Let Tk finish creating the native host window before starting Chrome.
        # There is deliberately no provider-specific intermediate panel here.
        self._launch_job = self._host.schedule_ui_callback(
            1,
            self._launch_and_embed,
        )

    def hide(self) -> None:
        """Detach the embedded X11 window and stop the managed browser."""
        if self._launch_job is not None:
            try:
                self._host.cancel_ui_callback(self._launch_job)
            except Exception:
                pass
            self._launch_job = None

        if self._embedder.window_id is not None:
            try:
                parent_id = int(self._host.screen_parent.winfo_toplevel().winfo_id())
                self._embedder.detach(parent_id)
            except (RuntimeError, tk.TclError):
                self._embedder.clear()

        self._player.stop()
        self._browser_host = None

    def _launch_and_embed(self) -> None:
        self._launch_job = None
        host = self._browser_host
        if host is None or not host.winfo_exists():
            return

        try:
            host.update_idletasks()
            width = max(1, host.winfo_width())
            height = max(1, host.winfo_height())
            position = (host.winfo_rootx(), host.winfo_rooty())
            display = os.environ.get("DISPLAY", ":1")

            self._player.play(
                self._default_target,
                display=display,
                window_position=position,
                window_size=(width, height),
            )

            self._embedder.embed(
                0,
                int(host.winfo_id()),
                width,
                height,
                window_class=self._window_class,
            )
            self._host.set_screen_status(f"{self._title} ready")
        except Exception as error:
            self._embedder.clear()
            self._host.set_screen_status(f"{self._title} launch failed: {error}")

    def _on_browser_host_resize(self, event: tk.Event) -> None:
        if self._embedder.window_id is not None:
            self._embedder.resize(max(1, event.width), max(1, event.height))
