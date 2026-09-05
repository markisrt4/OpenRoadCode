# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact map host used by the ORC home screen."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.shared_map_camera import get_shared_map_camera_runtime
from apps.orcUi.theme_runtime import theme_bundle
from ui.navigation import MapRequestHandlerIf
from ui.theme import ThemeBundle, ThemeMode


class HomeMapPanel(tk.Frame):
    """Provide the HOME navigation card and its native renderer host."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        map_request_handler: MapRequestHandlerIf | None = None,
        theme: ThemeBundle | None = None,
    ) -> None:
        self._theme = theme or self._theme_for_parent(parent)
        ui = self._theme.ui
        super().__init__(
            parent,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        runtime = get_shared_map_camera_runtime()
        self._request_handler = map_request_handler or runtime.request_handler
        self._map_host: tk.Frame
        self._build()
        self._schedule_renderer_refresh()

    @staticmethod
    def _theme_for_parent(parent: tk.Misc) -> ThemeBundle:
        """Resolve the active packaged theme for panels created after a toggle."""
        try:
            background = str(parent.cget("background")).lower()
        except (AttributeError, tk.TclError):
            background = ""
        mode = ThemeMode.LIGHT if background == "#e8edf0" else ThemeMode.DARK
        return theme_bundle(mode)

    @property
    def map_host_window_id(self) -> int:
        self.update_idletasks()
        return self._map_host.winfo_id()

    def _build(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # The native map renderer paints over this host. Keep the host itself
        # neutral and let MapLibre own the actual map palette.
        self._map_host = tk.Frame(self, bg=self._theme.ui.background)
        self._map_host.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

    def _schedule_renderer_refresh(self) -> None:
        # PUB/SUB drops commands until the newly launched renderer has joined.
        # Replay a few times so a host-window switch cannot strand the renderer
        # at its default camera if the first state message arrives too early.
        for delay_ms in (300, 700, 1200):
            self.after(delay_ms, self._refresh_renderer_state)

    def _refresh_renderer_state(self) -> None:
        refresh = getattr(self._request_handler, "refresh_renderer_state", None)
        if refresh is not None:
            refresh()
