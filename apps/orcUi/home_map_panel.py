# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact map host used by the ORC home screen."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.map_camera_runtime import MapCameraRuntime

PANEL = "#0b1117"
BORDER = "#25313b"
BLUE = "#168bd1"


class HomeMapPanel(tk.Frame):
    """Provide the HOME navigation card and its native renderer host."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self._map_host: tk.Frame
        self._camera_runtime = MapCameraRuntime(
            zoom_level=16.5,
            pitch_rad=0.0,
            follow_enabled=True,
        )
        self._build()
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._camera_runtime.start()

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
        self._map_host.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=1,
            pady=(0, 1),
        )

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self:
            self._camera_runtime.close()
