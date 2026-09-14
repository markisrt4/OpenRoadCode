# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent left-side navigation for the integrated orcUi shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle
from .shell_metrics import FONT_CONTROL, SIDE_NAV_WIDTH


_NAV_LABELS = {"NAVIGATION": "NAV"}

_NAV_ICONS = {
    "HOME": "⌂",
    "NAVIGATION": "➤",
    "RADIO": "⌁",
    "VEHICLE": "◆",
    "LIGHTING": "☀",
    "GAMES": "◇",
    "MEDIA": "▶",
}


class OrcUiSideNav(tk.Frame):
    """Render and update the shell's primary navigation destinations."""

    WIDTH = SIDE_NAV_WIDTH

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        items: list[str],
        active: str,
        on_navigate: Callable[[str], None],
    ) -> None:
        super().__init__(parent, width=self.WIDTH)
        self._on_navigate = on_navigate
        self._buttons: dict[str, tk.Button] = {}
        self.pack_propagate(False)
        self.rebuild(theme=theme, items=items, active=active)

    def rebuild(self, *, theme: ThemeBundle, items: list[str], active: str) -> None:
        ui = theme.ui
        self.configure(bg=ui.background)
        for child in self.winfo_children():
            child.destroy()
        self._buttons.clear()
        for item in items:
            button = tk.Button(
                self,
                text=f"{_NAV_ICONS.get(item, '•')}  {_NAV_LABELS.get(item, item)}",
                command=lambda name=item: self._on_navigate(name),
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                font=("Sans", FONT_CONTROL, "bold"),
                height=3,
                pady=2,
            )
            button.pack(fill=tk.X, padx=4, pady=2)
            self._buttons[item] = button
        self.set_active(active=active, theme=theme)

    def set_active(self, *, active: str, theme: ThemeBundle) -> None:
        ui = theme.ui
        self.configure(bg=ui.background)
        for name, button in self._buttons.items():
            selected = name == active
            button.configure(
                fg="#ffffff" if selected else ui.control_text,
                bg=ui.control_active if selected else ui.control_background,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                highlightthickness=2 if selected else 1,
                highlightbackground=ui.accent_primary if selected else ui.border,
            )
