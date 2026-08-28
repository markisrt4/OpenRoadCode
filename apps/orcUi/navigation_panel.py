# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full navigation panel for the integrated ORC cockpit UI."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.navigation import MapRequestHandlerIf

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
BLUE = "#168bd1"


class NavigationPanel(tk.Frame):
    """Provide the navigation map host and renderer-neutral camera controls."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=BG)
        self._request_handler: MapRequestHandlerIf | None = None
        self._zoom_level = 16.5
        self._follow_enabled = True
        self._follow_button: tk.Button
        self._map_host: tk.Frame
        self._build(on_back)

    @property
    def map_host_window_id(self) -> int:
        """Return the native window id reserved for an embedded map renderer."""

        self.update_idletasks()
        return self._map_host.winfo_id()

    def set_map_request_handler(
        self,
        handler: MapRequestHandlerIf | None,
    ) -> None:
        """Connect semantic map controls to their request consumer."""

        self._request_handler = handler

    def set_follow_enabled(self, enabled: bool) -> None:
        """Update the visible follow-mode state."""

        self._follow_enabled = enabled
        self._follow_button.configure(
            text="FOLLOW  ON" if enabled else "FOLLOW  OFF",
            fg=GREEN if enabled else TEXT,
        )

    def _build(self, on_back: Callable[[], None]) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=BG, height=42)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        tk.Button(
            header,
            text="‹ HOME",
            command=on_back,
            bg=BG,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=GREEN,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(4, 12))

        tk.Label(
            header,
            text="NAVIGATION",
            bg=BG,
            fg=TEXT,
            font=("Sans", 14, "bold"),
        ).grid(row=0, column=1)

        tk.Label(
            header,
            text="MAPLIBRE",
            bg=BG,
            fg=BLUE,
            font=("Sans", 9, "bold"),
        ).grid(row=0, column=2, sticky="e", padx=8)

        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self._map_host = tk.Frame(
            body,
            bg="#020406",
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self._map_host.grid(row=0, column=0, sticky="nsew")

        tk.Label(
            self._map_host,
            text="MAP RENDERER",
            bg="#020406",
            fg="#53616c",
            font=("Sans", 16, "bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        controls = tk.Frame(body, bg=PANEL, width=112)
        controls.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        controls.grid_propagate(False)

        self._follow_button = tk.Button(
            controls,
            text="FOLLOW  ON",
            command=self._toggle_follow,
            bg=PANEL,
            fg=GREEN,
            activebackground="#101820",
            activeforeground=GREEN,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BORDER,
            font=("Sans", 9, "bold"),
            height=3,
        )
        self._follow_button.pack(fill=tk.X, padx=6, pady=(8, 5))

        for text, command in (
            ("+", lambda: self._change_zoom(1.0)),
            ("−", lambda: self._change_zoom(-1.0)),
            ("N", self._north_up),
            ("RECENTER", self._recenter),
        ):
            tk.Button(
                controls,
                text=text,
                command=command,
                bg=PANEL,
                fg=TEXT,
                activebackground="#101820",
                activeforeground=GREEN,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=BORDER,
                font=("Sans", 10, "bold"),
                height=2,
            ).pack(fill=tk.X, padx=6, pady=5)

        tk.Label(
            controls,
            text="manual camera\ndisables follow",
            bg=PANEL,
            fg=MUTED,
            font=("Sans", 8),
            justify=tk.CENTER,
        ).pack(side=tk.BOTTOM, pady=10)

    def _toggle_follow(self) -> None:
        enabled = not self._follow_enabled
        self.set_follow_enabled(enabled)
        if self._request_handler is not None:
            self._request_handler.request_follow(enabled)

    def _change_zoom(self, delta: float) -> None:
        self._zoom_level = max(1.0, min(22.0, self._zoom_level + delta))
        self.set_follow_enabled(False)
        if self._request_handler is not None:
            self._request_handler.request_zoom(self._zoom_level)

    def _north_up(self) -> None:
        self.set_follow_enabled(False)
        if self._request_handler is not None:
            self._request_handler.request_bearing(0.0)

    def _recenter(self) -> None:
        self.set_follow_enabled(True)
        if self._request_handler is not None:
            self._request_handler.request_recenter()
