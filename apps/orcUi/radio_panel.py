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
PURPLE = "#a25ce5"

RADIO_GROUPS = ("FM", "WEATHER", "AIR", "HAM", "SCANNER", "EXPLORE")


class RadioPanel(tk.Frame):
    """Automotive controls wrapped around an embedded SDR++ viewport."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None],
        embedder: X11WindowEmbedder | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._embedder = embedder or X11WindowEmbedder()
        self._active_group = "FM"
        self._group_buttons: dict[str, tk.Button] = {}
        self._status: tk.Label
        self._host: tk.Frame

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Button(
            header,
            text="‹ HOME",
            command=on_back,
            bg="#101820",
            fg=TEXT,
            activebackground="#17232d",
            activeforeground=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT)
        tk.Label(
            header,
            text="RADIO",
            fg=PURPLE,
            bg=BG,
            font=("Sans", 13, "bold"),
        ).pack(side=tk.LEFT, padx=14)
        self._status = tk.Label(
            header,
            text="SDR++ NOT ATTACHED",
            fg=MUTED,
            bg=BG,
            font=("Monospace", 9),
        )
        self._status.pack(side=tk.RIGHT, padx=4)

        groups = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        groups.grid(row=1, column=0, sticky="ew", pady=(0, 6))
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
        body.grid(row=2, column=0, sticky="nsew")
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

        presets = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        presets.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        tk.Button(presets, text="‹ PRESET", bg=PANEL, fg=TEXT, relief=tk.FLAT, bd=0, padx=14, pady=7).pack(side=tk.LEFT)
        tk.Label(presets, text="101.1 FM", bg=PANEL, fg=TEXT, font=("Sans", 12, "bold")).pack(side=tk.LEFT, expand=True)
        tk.Button(presets, text="PRESET ›", bg=PANEL, fg=TEXT, relief=tk.FLAT, bd=0, padx=14, pady=7).pack(side=tk.RIGHT)

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

    def attach_sdrpp(self, process_id: int = 0) -> int:
        """Attach an existing SDR++ window to the panel.

        The title fallback is intentional for Termux/proot where the X11 window
        does not expose process metadata that xdotool can use.
        """
        self.update_idletasks()
        window_id = self._embedder.embed(
            process_id,
            self.host_window_id,
            self._host.winfo_width(),
            self._host.winfo_height(),
            window_name="SDR++",
        )
        self._status.configure(text=f"SDR++ ATTACHED  XID {window_id}", fg=GREEN)
        return window_id

    def clear_embedding(self) -> None:
        """Forget the embedded window when the SDR++ client exits."""
        self._embedder.clear()
        self._status.configure(text="SDR++ NOT ATTACHED", fg=MUTED)

    def _on_host_resize(self, event: tk.Event) -> None:
        self._embedder.resize(event.width, event.height)

    def _paint_groups(self) -> None:
        for name, button in self._group_buttons.items():
            active = name == self._active_group
            button.configure(
                fg=GREEN if active else TEXT,
                bg="#101820" if active else PANEL,
            )
