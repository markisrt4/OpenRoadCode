# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Shared disabled-map presentation for HOME and NAV."""

import tkinter as tk

from ui.theme import ThemeBundle


class MapDisabledPlaceholder(tk.Frame):
    """Centered map icon and status, independent of native rendering."""

    def __init__(self, parent: tk.Misc, theme: ThemeBundle) -> None:
        super().__init__(parent, bg=theme.ui.background)
        self._icon = tk.Canvas(self, width=48, height=40, highlightthickness=0)
        self._icon.pack(pady=(0, 6))
        self._heading = tk.Label(self, text="MAP DISABLED", font=("Sans", 16, "bold"))
        self._heading.pack()
        self._detail = tk.Label(
            self,
            text="Map rendering disabled by\nruntime configuration",
            font=("Sans", 10),
            justify=tk.CENTER,
        )
        self._detail.pack(pady=(4, 0))
        self.set_theme_bundle(theme)
        self.place(relx=0.5, rely=0.5, anchor="center")

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        ui = theme.ui
        self.configure(bg=ui.background)
        self._icon.configure(bg=ui.background)
        self._icon.delete("all")
        self._icon.create_polygon(
            5,
            10,
            17,
            5,
            31,
            10,
            43,
            5,
            43,
            30,
            31,
            35,
            17,
            30,
            5,
            35,
            fill="",
            outline=ui.text_muted,
            width=2,
        )
        for x, top, bottom in ((17, 5, 30), (31, 10, 35)):
            self._icon.create_line(x, top, x, bottom, fill=ui.text_muted, width=2)
        self._heading.configure(bg=ui.background, fg=ui.text)
        self._detail.configure(bg=ui.background, fg=ui.text_muted)
