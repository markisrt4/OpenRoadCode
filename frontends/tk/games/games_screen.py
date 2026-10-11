# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Present Games through inventory, runtime-host, and session contracts."""

from __future__ import annotations

from collections.abc import Callable
from common.resource_cleanup import ResourceCleanup, close_resources
import tkinter as tk

from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.games.games_session_if import GamesSessionIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode

from .games_panel import GamesPanel


class GamesScreen(TkScreen):
    """Render the Games destination; composition supplies its lifecycle handler."""

    def __init__(
        self, host: TkScreenHostIf, *, session: GamesSessionIf,
        theme_bundle: Callable[[], ThemeBundle], theme_mode: Callable[[], ThemeMode],
    ) -> None:
        super().__init__(ScreenId("games"))
        self._host = host
        self._session = session
        self._theme_bundle = theme_bundle
        self._theme_mode = theme_mode
        self._panel: GamesPanel | None = None
        self._resize_callback_id: object | None = None
        self._pending_size: tuple[int, int] | None = None
        self._loading_label: tk.Label | None = None
        self._closed = False
        self._on_resize: Callable[[int, int], None] | None = None

    def show(self) -> None:
        if self._closed:
            return
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("GAMES")
        panel = GamesPanel(self._host.screen_parent, theme=self._theme_bundle())
        panel.pack(fill=tk.BOTH, expand=True)
        self._panel = panel
        with ResourceCleanup() as cleanup:
            cleanup.callback(self.hide)
            self._session.activate(panel, self)
            cleanup.release()

    def hide(self) -> None:
        try:
            close_resources(self._session.deactivate, self._cancel_resize, self._clear_loading)
        finally:
            self._pending_size = None
            self._on_resize = None
            self._panel = None

    def shutdown(self) -> None:
        """Retire presentation and the composition-owned session exactly once."""
        if self._closed:
            return
        self._closed = True
        close_resources(self.hide, self._session.close)

    def show_runtime_host(self, on_resize: Callable[[int, int], None]) -> tuple[int, int, int]:
        """Create the toolkit host without exposing processes or platform adapters."""
        self._on_resize = on_resize
        panel = self._panel
        if panel is None:
            raise RuntimeError("Games screen is not active")
        return panel.show_runtime_host(self._resize_runtime)

    def set_runtime_loading(self, loading: bool) -> None:
        """Render the controller's launch indicator state."""
        panel = self._panel
        if loading and panel is not None:
            self._show_loading(panel)
        else:
            self._clear_loading()

    def hide_runtime_host(self) -> None:
        """Restore inventory after stopping a native game."""
        self._cancel_resize()
        self._pending_size = None
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.hide_runtime_host()

    def set_theme_mode(self, mode: ThemeMode) -> None:
        del mode
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.set_theme_bundle(self._theme_bundle())
        self._paint_loading()

    def _paint_loading(self) -> None:
        label = self._loading_label
        if label is not None and label.winfo_exists():
            ui = self._theme_bundle().ui
            label.configure(bg=ui.background, fg=ui.text)

    def _show_loading(self, panel: GamesPanel) -> None:
        self._clear_loading()
        ui = self._theme_bundle().ui
        label = tk.Label(
            panel, text="Now Loading ...", bg=ui.background, fg=ui.text,
            font=("Sans", 20, "bold"), padx=24, pady=16,
        )
        label.place(relx=0.5, rely=0.5, anchor="center")
        self._loading_label = label
        label.update_idletasks()

    def _clear_loading(self) -> None:
        label = self._loading_label
        self._loading_label = None
        if label is not None:
            try:
                label.destroy()
            except tk.TclError:
                pass

    def _resize_runtime(self, width: int, height: int) -> None:
        self._pending_size = (width, height)
        self._cancel_resize()
        self._resize_callback_id = self._host.schedule_ui_callback(75, self._dispatch_resize)

    def _cancel_resize(self) -> None:
        callback_id = self._resize_callback_id
        self._resize_callback_id = None
        if callback_id is None:
            return
        try:
            self._host.cancel_ui_callback(callback_id)
        except (RuntimeError, tk.TclError):
            pass

    def _dispatch_resize(self) -> None:
        self._resize_callback_id = None
        size = self._pending_size
        self._pending_size = None
        if size is None:
            return
        callback = self._on_resize
        if callback is not None:
            callback(*size)
