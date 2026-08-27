# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Switchable secondary context rail for the ORC cockpit home screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass


PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#79c83d"
BLUE = "#3297e5"
YELLOW = "#d6ad22"


@dataclass(frozen=True)
class ContextPage:
    """Description of one context-rail page."""

    name: str
    accent: str
    builder: Callable[[tk.Frame], None]


class ContextRail(tk.Frame):
    """Compact, user-switchable secondary information panel."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
        )

        self._pages = (
            ContextPage("VEHICLE", GREEN, self._build_vehicle),
            ContextPage("TRIP", BLUE, self._build_trip),
            ContextPage("OFF-ROAD", YELLOW, self._build_offroad),
        )
        self._page_index = 0

        self._title = tk.Label(
            self,
            text="",
            bg=PANEL,
            font=("Sans", 10, "bold"),
        )
        self._body = tk.Frame(self, bg=PANEL)

        self._build_header()
        self._body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 10))
        self._show_page()

    @property
    def selected_page(self) -> str:
        """Return the currently selected context page name."""

        return self._pages[self._page_index].name

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=PANEL)
        header.pack(fill=tk.X, padx=8, pady=(7, 3))
        header.grid_columnconfigure(1, weight=1)

        self._nav_button(header, "‹", self._previous_page).grid(
            row=0, column=0, sticky="w"
        )
        self._title.grid(row=0, column=1)
        self._nav_button(header, "›", self._next_page).grid(
            row=0, column=2, sticky="e"
        )

    @staticmethod
    def _nav_button(
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=PANEL,
            fg=TEXT,
            activebackground="#121b23",
            activeforeground=TEXT,
            relief=tk.FLAT,
            bd=0,
            width=3,
            font=("Sans", 16, "bold"),
            cursor="hand2",
        )

    def _previous_page(self) -> None:
        self._page_index = (self._page_index - 1) % len(self._pages)
        self._show_page()

    def _next_page(self) -> None:
        self._page_index = (self._page_index + 1) % len(self._pages)
        self._show_page()

    def _show_page(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()

        page = self._pages[self._page_index]
        self._title.configure(text=page.name, fg=page.accent)
        page.builder(self._body)

        dots = tk.Frame(self._body, bg=PANEL)
        dots.pack(side=tk.BOTTOM, pady=(4, 0))
        for index in range(len(self._pages)):
            tk.Label(
                dots,
                text="●" if index == self._page_index else "·",
                fg=page.accent if index == self._page_index else MUTED,
                bg=PANEL,
                font=("Sans", 9),
            ).pack(side=tk.LEFT, padx=2)

    def _build_vehicle(self, parent: tk.Frame) -> None:
        self._metric_table(
            parent,
            (
                ("Speed", "--", "MPH"),
                ("RPM", "--", "RPM"),
                ("Boost", "--", "PSI"),
                ("Coolant", "--", "°F"),
                ("Voltage", "--", "V"),
                ("Fuel", "--", "%"),
            ),
        )

    def _build_trip(self, parent: tk.Frame) -> None:
        self._metric_table(
            parent,
            (
                ("Distance", "--.-", "mi"),
                ("Elapsed", "--:--", ""),
                ("Avg speed", "--", "MPH"),
                ("Moving", "--:--", ""),
                ("Fuel used", "--.-", "gal"),
                ("Economy", "--.-", "MPG"),
            ),
        )

    def _build_offroad(self, parent: tk.Frame) -> None:
        compass = tk.Label(
            parent,
            text="N\n↑\n---°",
            fg=YELLOW,
            bg=PANEL,
            font=("Sans", 16, "bold"),
            justify=tk.CENTER,
        )
        compass.pack(pady=(4, 8))
        self._metric_table(
            parent,
            (
                ("Altitude", "----", "ft"),
                ("Pitch", "--.-", "°"),
                ("Roll", "--.-", "°"),
                ("GPS", "--", "sats"),
            ),
        )

    @staticmethod
    def _metric_table(
        parent: tk.Frame,
        metrics: tuple[tuple[str, str, str], ...],
    ) -> None:
        grid = tk.Frame(parent, bg=PANEL)
        grid.pack(fill=tk.BOTH, expand=True)
        grid.grid_columnconfigure(0, weight=2)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_columnconfigure(2, weight=1)

        for row, (label, value, unit) in enumerate(metrics):
            tk.Label(
                grid,
                text=label,
                fg=MUTED,
                bg=PANEL,
                font=("Sans", 9),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(2, 4), pady=3)
            tk.Label(
                grid,
                text=value,
                fg=TEXT,
                bg=PANEL,
                font=("Sans", 12, "bold"),
                anchor="e",
            ).grid(row=row, column=1, sticky="e", padx=4, pady=3)
            tk.Label(
                grid,
                text=unit,
                fg=MUTED,
                bg=PANEL,
                font=("Sans", 8),
                anchor="w",
            ).grid(row=row, column=2, sticky="w", padx=(0, 2), pady=3)
