# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Entry point for the integrated OpenRoadCode automotive UI."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime

from apps.orcUi.context_rail import ContextRail


BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#79c83d"
BLUE = "#3297e5"
PURPLE = "#a25ce5"
YELLOW = "#d6ad22"
RED = "#e35d6a"


class OrcUiApp:
    """Top-level ORC cockpit shell."""

    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.title("OpenRoadCode")
        self._root.geometry("1024x600")
        self._root.minsize(1024, 600)
        self._root.configure(bg=BG)

        self._active_nav = "HOME"
        self._nav_buttons: dict[str, tk.Button] = {}
        self._clock_label: tk.Label
        self._content: tk.Frame
        self._volume = 20
        self._volume_label: tk.Label

        self._build_shell()
        self._show_home()
        self._update_clock()

    def run(self) -> None:
        self._root.mainloop()

    def _build_shell(self) -> None:
        self._root.grid_rowconfigure(1, weight=1)
        self._root.grid_columnconfigure(1, weight=1)
        self._build_top_bar()
        self._build_side_nav()
        self._content = tk.Frame(self._root, bg=BG)
        self._content.grid(row=1, column=1, sticky="nsew", padx=(6, 8), pady=6)
        self._build_bottom_bar()
        self._build_footer()

    def _build_top_bar(self) -> None:
        bar = tk.Frame(self._root, bg="#020406", height=50)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        brand = tk.Frame(bar, bg="#020406")
        brand.grid(row=0, column=0, sticky="w", padx=18)
        tk.Label(brand, text="▲", fg=GREEN, bg="#020406", font=("Sans", 19, "bold")).pack(side=tk.LEFT, padx=(0, 7))
        tk.Label(brand, text="O", fg=GREEN, bg="#020406", font=("Sans", 22, "bold")).pack(side=tk.LEFT)
        tk.Label(brand, text="R", fg=BLUE, bg="#020406", font=("Sans", 22, "bold")).pack(side=tk.LEFT)
        tk.Label(brand, text="C", fg=PURPLE, bg="#020406", font=("Sans", 22, "bold")).pack(side=tk.LEFT)

        self._clock_label = tk.Label(bar, fg=TEXT, bg="#020406", font=("Sans", 17, "bold"))
        self._clock_label.grid(row=0, column=1)
        tk.Label(
            bar,
            text="GPS  ▮▮▮   WiFi   BT   🚗",
            fg="#b8c0c6",
            bg="#020406",
            font=("Sans", 11),
        ).grid(row=0, column=2, padx=18)

    def _build_side_nav(self) -> None:
        nav = tk.Frame(self._root, bg="#070c11", width=112)
        nav.grid(row=1, column=0, sticky="ns", padx=(8, 0), pady=6)
        nav.grid_propagate(False)
        items = ["HOME", "NAVIGATION", "RADIO", "VEHICLE", "LIGHTING", "CONTROLS", "SETTINGS"]
        for item in items:
            button = tk.Button(nav, text=item, command=lambda name=item: self._select_nav(name), bg="#070c11", fg="#c7cdd2", activebackground="#101820", activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 9), height=3, cursor="hand2")
            button.pack(fill=tk.X, padx=4, pady=2)
            self._nav_buttons[item] = button
        self._paint_nav()

    def _build_bottom_bar(self) -> None:
        bar = tk.Frame(self._root, bg=BG, height=55)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 5))
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=2)
        for col in range(1, 6):
            bar.grid_columnconfigure(col, weight=1)

        volume = tk.Frame(bar, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        volume.grid(row=0, column=0, sticky="nsew", padx=3)
        volume.grid_columnconfigure(1, weight=1)
        tk.Button(volume, text="−", command=lambda: self._change_volume(-5), bg=PANEL, fg=TEXT, activebackground="#121b23", activeforeground=TEXT, relief=tk.FLAT, bd=0, font=("Sans", 16, "bold")).grid(row=0, column=0, sticky="ns", padx=4)
        self._volume_label = tk.Label(volume, text="🔊 20%", bg=PANEL, fg=TEXT, font=("Sans", 10, "bold"))
        self._volume_label.grid(row=0, column=1)
        tk.Button(volume, text="+", command=lambda: self._change_volume(5), bg=PANEL, fg=TEXT, activebackground="#121b23", activeforeground=TEXT, relief=tk.FLAT, bd=0, font=("Sans", 15, "bold")).grid(row=0, column=2, sticky="ns", padx=4)

        actions = ["🎙  Push to Talk", "▣  Front Cam", "▣  SCREEN\nAuto", "☀  BRIGHTNESS\n70%", "↪  EXIT"]
        for col, text in enumerate(actions, start=1):
            command = self._root.destroy if text.endswith("EXIT") else None
            tk.Button(bar, text=text, command=command, bg=PANEL, fg=TEXT, activebackground="#121b23", activeforeground=TEXT, relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER, font=("Sans", 9)).grid(row=0, column=col, sticky="nsew", padx=3)

    def _change_volume(self, delta: int) -> None:
        self._volume = max(0, min(100, self._volume + delta))
        icon = "🔇" if self._volume == 0 else "🔊"
        self._volume_label.configure(text=f"{icon} {self._volume}%")

    def _build_footer(self) -> None:
        footer = tk.Frame(self._root, bg="#020406", height=25)
        footer.grid(row=3, column=0, columnspan=2, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(1, weight=1)
        tk.Label(footer, text="OpenRoadCode", fg="#aab2b8", bg="#020406", font=("Sans", 8)).grid(row=0, column=0, padx=10)
        tk.Label(footer, text="Services: --   |   ZMQ: --", fg=MUTED, bg="#020406", font=("Sans", 8)).grid(row=0, column=1)
        tk.Label(footer, text="orcUi prototype", fg=MUTED, bg="#020406", font=("Sans", 8)).grid(row=0, column=2, padx=10)

    def _select_nav(self, name: str) -> None:
        self._active_nav = name
        self._paint_nav()
        self._show_home() if name == "HOME" else self._show_placeholder(name)

    def _paint_nav(self) -> None:
        for name, button in self._nav_buttons.items():
            active = name == self._active_nav
            button.configure(fg=GREEN if active else "#c7cdd2", bg="#101820" if active else "#070c11")

    def _clear_content(self) -> None:
        for child in self._content.winfo_children():
            child.destroy()

    def _show_home(self) -> None:
        self._clear_content()
        self._active_nav = "HOME"
        self._paint_nav()
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_columnconfigure(1, weight=0, minsize=ContextRail.WIDTH)
        self._content.grid_rowconfigure(0, weight=3)
        self._content.grid_rowconfigure(1, weight=2)

        map_panel = self._panel(self._content, "NAVIGATION", BLUE)
        map_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
        tk.Label(map_panel, text="MAP / ROUTE VIEW", fg="#53616c", bg=PANEL, font=("Sans", 18, "bold")).place(relx=.5, rely=.5, anchor="center")

        context = ContextRail(self._content, on_expand=self._show_context_full_panel)
        context.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))

        lower = tk.Frame(self._content, bg=BG)
        lower.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(5, 0))
        lower.grid_columnconfigure(0, weight=1)
        lower.grid_columnconfigure(1, weight=1)
        lower.grid_rowconfigure(0, weight=1)

        radio = self._panel(lower, "RADIO", PURPLE)
        radio.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self._summary(radio, "101.1 FM", "Radio service")

        media = self._panel(lower, "MEDIA", BLUE)
        media.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self._summary(media, "No media", "Playback service")
        tk.Label(media, text="▂▅▃▇▄▆▂▅", fg=BLUE, bg=PANEL, font=("Sans", 14, "bold")).pack(anchor="w", padx=16, pady=(7, 0))

    def _show_context_full_panel(self, name: str) -> None:
        self._clear_content()
        accent = {"VEHICLE": GREEN, "TRIP": BLUE, "OFF-ROAD": YELLOW}.get(name, GREEN)
        panel = self._panel(self._content, name, accent)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Button(panel, text="‹ HOME", command=self._show_home, bg="#101820", fg=TEXT, activebackground="#18232d", activeforeground=TEXT, relief=tk.FLAT, font=("Sans", 11, "bold"), padx=14, pady=7).pack(anchor="nw", padx=14, pady=10)
        tk.Label(panel, text=f"FULL {name} PANEL", fg=accent, bg=PANEL, font=("Sans", 28, "bold")).place(relx=.5, rely=.44, anchor="center")
        tk.Label(panel, text="This surface is ready for the dedicated panel implementation.", fg=MUTED, bg=PANEL, font=("Sans", 11)).place(relx=.5, rely=.55, anchor="center")

    def _show_placeholder(self, name: str) -> None:
        self._clear_content()
        panel = self._panel(self._content, name, GREEN)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(panel, text=f"{name}\nCOMING NEXT", fg=TEXT, bg=PANEL, font=("Sans", 24, "bold"), justify=tk.CENTER).place(relx=.5, rely=.5, anchor="center")

    @staticmethod
    def _panel(parent: tk.Misc, title: str, accent: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        tk.Label(frame, text=title, fg=accent, bg=PANEL, font=("Sans", 10, "bold")).pack(anchor="nw", padx=14, pady=(11, 4))
        return frame

    @staticmethod
    def _summary(parent: tk.Frame, primary: str, secondary: str) -> None:
        tk.Label(parent, text=primary, fg=TEXT, bg=PANEL, font=("Sans", 14, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(parent, text=secondary, fg=MUTED, bg=PANEL, font=("Sans", 9)).pack(anchor="w", padx=16)

    def _update_clock(self) -> None:
        now = datetime.now()
        self._clock_label.configure(text=now.strftime("%I:%M %p     %a, %b %d").lstrip("0"))
        self._root.after(1000, self._update_clock)


def main() -> None:
    OrcUiApp().run()


if __name__ == "__main__":
    main()
