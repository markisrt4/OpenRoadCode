# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi radio panel hosting the SDR++ X11 client."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.x11 import X11WindowEmbedder

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"

RADIO_GROUPS = ("FM", "WEATHER", "AIR", "HAM", "SCANNER", "EXPLORE")


class RadioPanel(tk.Frame):
    """Automotive controls wrapped around an embedded SDR++ viewport."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        embedder: X11WindowEmbedder | None = None,
        on_previous_preset: Callable[[], None] | None = None,
        on_next_preset: Callable[[], None] | None = None,
        on_tune_down: Callable[[], None] | None = None,
        on_tune_up: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._embedder = embedder or X11WindowEmbedder()
        self._active_group = "FM"
        self._group_buttons: dict[str, tk.Button] = {}
        self._station_label: tk.Label
        self._frequency_label: tk.Label
        self._host: tk.Frame

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        groups = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        groups.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        for name in RADIO_GROUPS:
            button = tk.Button(
                groups,
                text=name,
                command=lambda group=name: self.select_group(group),
                bg=PANEL,
                fg=TEXT,
                activebackground="#17232d",
                activeforeground=GREEN,
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9, "bold"),
                padx=10,
                pady=7,
            )
            button.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._group_buttons[name] = button
        self._paint_groups()

        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._host = tk.Frame(
            body,
            bg="#000000",
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self._host.grid(row=0, column=0, sticky="nsew")
        self._host.bind("<Configure>", self._on_host_resize)

        controls = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        controls.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        controls.grid_columnconfigure(2, weight=1)

        tk.Button(
            controls,
            text="‹ PRESET",
            command=on_previous_preset,
            bg=PANEL,
            fg=TEXT,
            activebackground="#17232d",
            activeforeground=GREEN,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=7,
        ).grid(row=0, column=0, rowspan=2, sticky="ns")
        tk.Button(
            controls,
            text="− TUNE",
            command=on_tune_down,
            bg=PANEL,
            fg=MUTED,
            activebackground="#17232d",
            activeforeground=GREEN,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=7,
        ).grid(row=0, column=1, rowspan=2, sticky="ns")

        center = tk.Frame(controls, bg=PANEL)
        center.grid(row=0, column=2, rowspan=2, sticky="ew")
        self._station_label = tk.Label(
            center,
            text="NO PRESET",
            bg=PANEL,
            fg=TEXT,
            font=("Sans", 11, "bold"),
        )
        self._station_label.pack()
        self._frequency_label = tk.Label(
            center,
            text="--.- MHz",
            bg=PANEL,
            fg=MUTED,
            font=("Monospace", 9),
        )
        self._frequency_label.pack()

        tk.Button(
            controls,
            text="TUNE +",
            command=on_tune_up,
            bg=PANEL,
            fg=MUTED,
            activebackground="#17232d",
            activeforeground=GREEN,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=7,
        ).grid(row=0, column=3, rowspan=2, sticky="ns")
        tk.Button(
            controls,
            text="PRESET ›",
            command=on_next_preset,
            bg=PANEL,
            fg=TEXT,
            activebackground="#17232d",
            activeforeground=GREEN,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=7,
        ).grid(row=0, column=4, rowspan=2, sticky="ns")

    @property
    def host_window_id(self) -> int:
        """Return the X11 window id used as the SDR++ parent."""
        self.update_idletasks()
        return int(self._host.winfo_id())

    @property
    def active_group(self) -> str:
        return self._active_group

    def select_group(self, name: str) -> None:
        """Select an ORC radio group without changing SDR++ state yet."""
        if name not in RADIO_GROUPS:
            raise ValueError(f"Unknown radio group: {name}")
        self._active_group = name
        self._paint_groups()

    def set_station(self, label: str, frequency_hz: int, mode_name: str | None = None) -> None:
        """Display the active ORC station/preset independently of SDR++ chrome."""
        self._station_label.configure(text=label)
        frequency_mhz = frequency_hz / 1_000_000
        suffix = f"   {mode_name}" if mode_name else ""
        self._frequency_label.configure(text=f"{frequency_mhz:.3f} MHz{suffix}")

    def attach_sdrpp(self, process_id: int = 0) -> int:
        """Attach an existing SDR++ window to the panel."""
        self.update_idletasks()
        return self._embedder.embed(
            process_id,
            self.host_window_id,
            self._host.winfo_width(),
            self._host.winfo_height(),
            window_name="SDR++",
        )

    def detach_sdrpp(self, parent_window_id: int) -> None:
        """Keep SDR++ alive while this transient panel is destroyed."""
        self._embedder.detach(parent_window_id)

    def clear_embedding(self) -> None:
        """Forget the embedded window when the SDR++ client exits."""
        self._embedder.clear()

    def _on_host_resize(self, event: tk.Event) -> None:
        self._embedder.resize(event.width, event.height)

    def _paint_groups(self) -> None:
        for name, button in self._group_buttons.items():
            active = name == self._active_group
            button.configure(
                fg=GREEN if active else TEXT,
                bg="#101820" if active else PANEL,
            )
