# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract-based Tk screen for radio source selection and SDR presentation."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from frontends.x11.x11_window_embedder import X11WindowEmbedder
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode

RadioPanelFactory = Callable[[tk.Misc, X11WindowEmbedder, ThemeBundle], tk.Widget]
ThemeBundleProvider = Callable[[], ThemeBundle]
ThemeSyncHandler = Callable[[ThemeMode], None]


class RadioScreen(TkScreen):
    """Compose radio UI and native SDR embedding behind ``ScreenUiIf``."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme_bundle: ThemeBundleProvider,
        panel_factory: RadioPanelFactory,
        sync_theme: ThemeSyncHandler | None = None,
    ) -> None:
        super().__init__(ScreenId("radio"))
        self._host = host
        self._theme_bundle = theme_bundle
        self._panel_factory = panel_factory
        self._sync_theme = sync_theme
        self._embedder = X11WindowEmbedder()
        self._panel: tk.Widget | None = None

    def show(self) -> None:
        """Build the radio chooser and make it the active screen."""
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("RADIO")

        theme = self._theme_bundle()
        self._sync_external_theme(theme.mode)
        panel = self._panel_factory(self._host.screen_parent, self._embedder, theme)
        panel.pack(fill=tk.BOTH, expand=True)
        self._panel = panel

    def hide(self) -> None:
        """Detach any embedded SDR window before the host destroys content."""
        panel = self._panel
        self._panel = None
        if panel is not None and panel.winfo_exists():
            detach = getattr(panel, "detach_sdrpp", None)
            if callable(detach):
                try:
                    detach(panel.winfo_toplevel().winfo_id())
                except (RuntimeError, tk.TclError):
                    pass
        self._embedder.clear()

    def set_theme_mode(self, mode: ThemeMode) -> None:
        """Keep external SDR presentation aligned with the application theme."""
        self._sync_external_theme(mode)

    def _sync_external_theme(self, mode: ThemeMode) -> None:
        handler = self._sync_theme
        if handler is not None:
            handler(mode)
