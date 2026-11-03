# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Screen adapter for browser-backed media destinations."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable

from ui.media.browser_player_if import BrowserMediaPlayerIf, BrowserThemeRequestHandlerIf, HostedSurfaceGeometryIf
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from frontends.x11 import X11WindowEmbedder
from frontends.x11.window_embedder_if import WindowEmbedderIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle

MediaNavigationFactory = Callable[[tk.Misc, str], tk.Widget]


class BrowserMediaScreen(TkScreen):
    """Launch and reparent one managed browser directly into an ORC screen."""

    def __init__(
        self, screen_id: str, host: TkScreenHostIf, *, title: str,
        player: BrowserMediaPlayerIf, default_target: str, window_class: str | None,
        back_action: Callable[[], None],
        media_navigation_factory: MediaNavigationFactory | None = None,
        theme_bundle: Callable[[], ThemeBundle] | None = None,
        theme_request_handler: BrowserThemeRequestHandlerIf | None = None,
        preserve_external_window: bool = False,
        surface_geometry: HostedSurfaceGeometryIf | None = None,
        window_embedder: WindowEmbedderIf | None = None,
        window_name: str | Callable[[], str | None] | None = None,
        back_label: str | None = None,
        keep_player_on_hide: bool = False,
        close_action: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(ScreenId(screen_id))
        self._host = host
        self._title = title
        self._player = player
        self._default_target = default_target
        self._window_class = window_class
        self._window_name = window_name
        self._back_action = back_action
        self._back_label = back_label
        self._keep_player_on_hide = keep_player_on_hide
        self._close_action = close_action
        self._media_navigation_factory = media_navigation_factory
        self._theme_provider = theme_bundle
        self._theme_request_handler = theme_request_handler
        self._preserve_external_window = preserve_external_window
        self._surface_geometry = surface_geometry
        self._vertical_crop = (0, 0)
        self._launch_job: object | None = None
        self._embedder = window_embedder if window_embedder is not None else X11WindowEmbedder()
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
        self._navigation = self._build_navigation(root)
        if self._navigation is not None:
            self._navigation.pack(fill=tk.X, padx=4, pady=(4, 2))
        browser_host = tk.Frame(root, bg=background)
        browser_host.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))
        browser_host.bind("<Configure>", self._on_browser_host_resize)
        self._browser_host = browser_host
        self._launch_job = self._host.schedule_ui_callback(1, self._launch_and_embed)

    def _build_navigation(self, root):
        if self._media_navigation_factory is not None:
            return self._media_navigation_factory(root, self.screen_id.value)
        if self._back_label is None and self._close_action is None:
            return None
        ui = self._theme_provider().ui if self._theme_provider is not None else None
        bar = tk.Frame(root, bg=self._background())
        tk.Button(bar, text=self._back_label, command=self._back_action,
                  bg=ui.control_background if ui else '#101b23',
                  fg=ui.control_text if ui else '#ffffff',
                  activebackground=ui.control_active if ui else '#20313e',
                  activeforeground=ui.text if ui else '#ffffff',
                  relief=tk.FLAT, bd=0, highlightthickness=0,
                  font=('Sans', 11, 'bold'), padx=12, pady=8).pack(side=tk.LEFT)
        if self._close_action is not None:
            tk.Button(bar, text='CLOSE WAZE', command=self._close_action,
                      bg=ui.control_background if ui else '#101b23',
                      fg=ui.control_text if ui else '#ffffff', relief=tk.FLAT,
                      bd=0, highlightthickness=0, font=('Sans', 11, 'bold'),
                      padx=12, pady=8).pack(side=tk.RIGHT)
        return bar

    def set_theme_mode(self, _mode: object) -> None:
        """Repaint ORC chrome and request the browser surface’s theme update."""
        if not self._visible:
            return
        background = self._background()
        for frame in (self._root, self._browser_host):
            if frame is not None and frame.winfo_exists():
                frame.configure(bg=background)
        if self._navigation is not None and self._root is not None and self._root.winfo_exists():
            self._navigation.destroy()
            self._navigation = None
            self._navigation = self._build_navigation(self._root)
            if self._navigation is not None:
                self._navigation.pack(fill=tk.X, padx=4, pady=(4, 2), before=self._browser_host)
        if self._theme_request_handler is not None:
            self._theme_request_handler.request_theme_refresh()
        else:
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
                parent_id = self._detach_parent_id()
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
                parent_id = self._detach_parent_id()
                self._embedder.detach(parent_id)
            except (RuntimeError, tk.TclError):
                self._embedder.clear()
        if not self._keep_player_on_hide:
            self._player.stop()
        self._browser_host = None
        self._root = None
        self._navigation = None

    def close_session(self) -> None:
        """Explicit teardown, including when the retained player is hidden."""
        self.hide()
        if self._keep_player_on_hide:
            self._player.stop()

    def _detach_parent_id(self) -> int:
        # A user-owned compositor must survive destruction of ORC's toplevel.
        if self._preserve_external_window or self._keep_player_on_hide:
            return self._embedder.root_window_id()
        return int(self._host.screen_parent.winfo_toplevel().winfo_id())

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
            if not self._player.play(self._default_target, display=display, window_position=position, window_size=(width, height)):
                self._host.set_screen_status(f"{self._title} unavailable")
                return
            options = {}
            window_name = self._window_name() if callable(self._window_name) else self._window_name
            if window_name is not None:
                options['window_name'] = window_name
            if self._surface_geometry is not None:
                self._vertical_crop = self._surface_geometry.vertical_crop()
            if self._preserve_external_window or self._keep_player_on_hide:
                options['failure_parent_window_id'] = self._detach_parent_id()
            if self._vertical_crop != (0, 0):
                options['vertical_crop'] = self._vertical_crop
            self._embedder.embed(0, int(host.winfo_id()), width, height,
                                 window_class=self._window_class, **options)
            self._host.set_screen_status(f"{self._title} ready")
        except Exception as error:
            self._embedder.clear()
            # A successful spawn followed by failed embedding must not leave an
            # unmanaged window holding this application's Chromium profile.
            try:
                self._player.stop()
            except Exception as cleanup_error:
                self._host.set_screen_status(
                    f"{self._title} launch failed: {error}; cleanup failed: {cleanup_error}"
                )
            else:
                self._host.set_screen_status(f"{self._title} launch failed: {error}")

    def _on_browser_host_resize(self, event: tk.Event) -> None:
        if self._embedder.window_id is not None:
            self._embedder.resize(max(1, event.width), max(1, event.height))
