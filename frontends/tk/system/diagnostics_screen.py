# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable Tk screen for live system diagnostics."""

from __future__ import annotations

from collections.abc import Callable

import tkinter as tk

from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.system_diagnostics import SystemDiagnosticsProviderIf, SystemDiagnosticsSnapshot
from ui.theme import ThemeBundle, ThemeMode

from .diagnostics_panel import DiagnosticsPanel


class DiagnosticsScreen(TkScreen):
    """Display a periodically refreshed read-only diagnostics snapshot."""

    _REFRESH_MS = 1000

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        provider: SystemDiagnosticsProviderIf,
        theme_bundle: Callable[[], ThemeBundle],
        on_back: Callable[[], None] | None = None,
        history: Callable[[], tuple[SystemDiagnosticsSnapshot, ...]] | None = None,
    ) -> None:
        super().__init__(ScreenId("DIAGNOSTICS"))
        self._host = host
        self._provider = provider
        self._theme_bundle = theme_bundle
        self._on_back = on_back
        self._history = history
        self._panel: DiagnosticsPanel | None = None
        self._refresh_callback_id: object | None = None

    def show(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("COMPUTING UNIT PERFORMANCE")
        ui = self._theme_bundle().ui
        if self._on_back is not None:
            tk.Button(self._host.screen_parent, text="‹ BACK", command=self._on_back,
                      bg=ui.control_background, fg=ui.control_text,
                      activebackground=ui.control_active, activeforeground=ui.control_text,
                      relief=tk.FLAT, bd=0, highlightthickness=1, highlightbackground=ui.border,
                      font=("Sans", 10, "bold"), padx=12, pady=7, cursor="hand2").pack(anchor="w", pady=(0, 6))

        panel = DiagnosticsPanel(
            self._host.screen_parent,
            theme=self._theme_bundle(),
        )
        panel.pack(fill=tk.BOTH, expand=True)
        self._panel = panel
        if self._history is not None:
            for snapshot in self._history():
                panel.apply_snapshot(snapshot)
        self._refresh()

    def hide(self) -> None:
        callback_id = self._refresh_callback_id
        self._refresh_callback_id = None
        if callback_id is not None:
            try:
                self._host.cancel_ui_callback(callback_id)
            except (RuntimeError, tk.TclError):
                pass
        self._panel = None

    def set_theme_mode(self, mode: ThemeMode) -> None:
        del mode
        if self._panel is not None:
            self.show()

    def _refresh(self) -> None:
        self._refresh_callback_id = None
        panel = self._panel
        if panel is None or not panel.winfo_exists():
            return
        try:
            snapshot = self._provider.snapshot()
        except Exception as error:
            self._host.set_screen_status(
                f"Diagnostics unavailable: {type(error).__name__}: {error}"
            )
        else:
            panel.apply_snapshot(snapshot)
            self._host.set_screen_status("Live system performance")
        if self._panel is panel:
            self._refresh_callback_id = self._host.schedule_ui_callback(
                self._REFRESH_MS,
                self._refresh,
            )
