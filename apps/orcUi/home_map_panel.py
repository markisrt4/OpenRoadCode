# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact map host used by the ORC home screen."""

from __future__ import annotations

import tkinter as tk

from ui.navigation import MapRequestHandlerIf

PANEL = "#0b1117"
BORDER = "#25313b"
BLUE = "#168bd1"


class HomeMapPanel(tk.Frame):
    """Provide the HOME navigation card and its native renderer host."""

    def __init__(self, parent: tk.Misc, *, map_request_handler: MapRequestHandlerIf) -> None:
        super().__init__(
            parent,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self._request_handler = map_request_handler
        self._map_host: tk.Frame
        self._build()

    @property
    def map_host_window_id(self) -> int:
        """Return the native X11 window id reserved for the map renderer."""
        self.update_idletasks()
        return self._map_host.winfo_id()

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        tk.Label(
            self,
            text="NAVIGATION",
            fg=BLUE,
            bg=PANEL,
            font=("Sans", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(11, 4))
        self._map_host = tk.Frame(self, bg="#020406")
        self._map_host.grid(row=1, column=0, sticky="nsew", padx=1, pady=(0, 1))
