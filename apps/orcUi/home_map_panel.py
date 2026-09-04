# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact map host used by the ORC home screen."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.shared_map_camera import get_shared_map_camera_runtime
from ui.navigation import MapRequestHandlerIf

PANEL = "#0b1117"
BORDER = "#25313b"


class HomeMapPanel(tk.Frame):
    """Provide the HOME navigation card and its native renderer host."""

    def __init__(self, parent: tk.Misc, *, map_request_handler: MapRequestHandlerIf | None = None) -> None:
        super().__init__(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        runtime = get_shared_map_camera_runtime()
        self._request_handler = map_request_handler or runtime.request_handler
        self._map_host: tk.Frame
        self._build()
        self._schedule_renderer_refresh()

    @property
    def map_host_window_id(self) -> int:
        self.update_idletasks()
        return self._map_host.winfo_id()

    def _build(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._map_host = tk.Frame(self, bg="#020406")
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
