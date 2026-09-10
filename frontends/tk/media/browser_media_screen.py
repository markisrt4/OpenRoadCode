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
from ui.theme import ThemeBundle

MediaNavigationFactory = Callable[[tk.Misc, str], tk.Widget]


class BrowserMediaScreen(TkScreen):
    """Launch and reparent one managed browser directly into an ORC screen."""

    def __init__(
        self, screen_id: str, host: TkScreenHostIf, *, title: str,
        player: BrowserMediaPlayerIf, default_target: str, window_class: str,
        back_action: Callable[[], None],
        media_navigation_factory: MediaNavigationFactory | None = None,
        theme_bundle: Callable[[], ThemeBundle] | None = None,
    ) -> None:
        super().__init__(ScreenId(screen_id))
        self._host = host
        self._title = title
        self._player = player
        self._default_target = default_target
        self._window_class = window_class
        self._back_action = back_action
        self._media_navigation_factory = media_navigation_factory
        self._theme_provider = theme_bundle
        self._launch_job: object | None = None
        self._embedder = X11WindowEmbedder()
        self._browser_host: tk.Frame | None = None
        self._root: tk.Frame | None = None
        self._navigation: tk.Widget | None = None
        self._visible = False

    def _background(self) -> str:
        return self._theme_provider().ui.background if self._theme_provider is not None else "#000000"

    def show(self) -> None:
        """Show media navigation and launch the provider directly below it."""
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title(self._title)
        self._host.set_screen_back_action(self._back_action)
        self._visible = True
        background = self._background()
        root = tk.Frame(self._host.screen_parent, bg=background)
        root.pack(fill=tk.BOTH, expand=True)
        self._root = root
        if self._media_navigation_factory is not None:
            self._navigation = self._media_navigation_factory(root, self.screen_id.value)
            self._navigation.pack(fill=tk.X, padx=4, pady=(4, 2))
        browser_host = tk.Frame(root, bg=background)
        browser_host.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))
        browser_host.bind("<Configure>", self._on_browser_host_resize)
        self._browser_host = browser_host
        self._launch_job = self._host.schedule_ui_callback(1, self._launch_and_embed)

    def set_theme_mode(self, _mode: object) -> None:
        """Repaint ORC chrome and relaunch Chromium with the new color scheme."""
        if not self._visible:
            return
        background = self._background()
        for frame in (self._root, self._browser_host):
            if frame is not None and frame.winfo_exists():
                frame.configure(bg=background)
        if self._navigation is not None and self._root is not None and self._root.winfo_exists():
            self._navigation.destroy()
            self._navigation = None
            if self._media_navigation_factory is not None:
                self._navigation = self._media_navigation_factory(self._root, self.screen_id.value)
                self._navigation.pack(fill=tk.X, padx=4, pady=(4, 2), before=self._browser_host)
        self._restart_browser_for_theme()

    def _restart_browser_for_theme(self) -> None:
        host = self._browser_host
        if host is None or not host.winfo_exists():
            return
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
        self._host.set_screen_status(f"Applying {self._title} theme…")
        self._launch_job = self._host.schedule_ui_callback(1, self._launch_and_embed)

    def hide(self) -> None:
        """Detach the embedded X11 window and stop the managed browser."""
        self._visible = False
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
        self._root = None
        self._navigation = None

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
            self._player.play(self._default_target, display=display, window_position=position, window_size=(width, height))
            self._embedder.embed(0, int(host.winfo_id()), width, height, window_class=self._window_class)
            self._host.set_screen_status(f"{self._title} ready")
        except Exception as error:
            self._embedder.clear()
            self._host.set_screen_status(f"{self._title} launch failed: {error}")

    def _on_browser_host_resize(self, event: tk.Event) -> None:
        if self._embedder.window_id is not None:
            self._embedder.resize(max(1, event.width), max(1, event.height))
