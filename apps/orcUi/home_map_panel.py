# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact map host used by the ORC home screen."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.shared_map_camera import get_shared_map_camera_runtime
from ui.navigation import MapRequestHandlerIf

PANEL = "#0b1117"
BORDER = "#25313b"
BLUE = "#168bd1"
_HOME_MAP_ZOOM = 12.0
_HOME_MAP_BEARING_RAD = 0.0
_HOME_MAP_PITCH_RAD = 0.0


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
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        tk.Label(self, text="NAVIGATION", fg=BLUE, bg=PANEL,
                 font=("Sans", 10, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(11, 4))
        self._map_host = tk.Frame(self, bg="#020406")
        self._map_host.grid(row=1, column=0, sticky="nsew", padx=1, pady=(0, 1))

    def _schedule_renderer_refresh(self) -> None:
        # PUB/SUB drops commands until the newly launched renderer has joined.
        # HOME is a presentation camera, not the navigation camera. With a
        # known position it shows a flat local overview; otherwise it asks the
        # renderer to frame the installed dataset instead of inventing (0, 0).
        for delay_ms in (300, 700, 1200):
            self.after(delay_ms, self._refresh_renderer_state)

    def _refresh_renderer_state(self) -> None:
        if bool(getattr(self._request_handler, "camera_initialized", False)):
            refresh = getattr(self._request_handler, "refresh_renderer_state", None)
            if refresh is not None:
                refresh(
                    zoom_level=_HOME_MAP_ZOOM,
                    bearing_rad=_HOME_MAP_BEARING_RAD,
                    pitch_rad=_HOME_MAP_PITCH_RAD,
                )
            return
        overview = getattr(self._request_handler, "request_dataset_overview", None)
        if overview is not None:
            overview()
