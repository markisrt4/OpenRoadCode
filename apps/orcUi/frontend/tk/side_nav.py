# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent left-side navigation for the integrated orcUi shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle
from .shell_metrics import FONT_CONTROL, SIDE_NAV_WIDTH


_NAV_LABELS = {"NAVIGATION": "NAV"}

class _NavTile(tk.Canvas):
    """Compact nav tile with a muted watermark icon behind the label."""

    HEIGHT = 64

    def __init__(
        self,
        parent: tk.Misc,
        *,
        name: str,
        theme: ThemeBundle,
        on_navigate: Callable[[str], None],
    ) -> None:
        self._nav_name = name
        self._theme = theme
        self._on_navigate = on_navigate
        self._selected = False
        self._hovered = False
        super().__init__(
            parent,
            height=self.HEIGHT,
            highlightthickness=1,
            bd=0,
            cursor="hand2",
        )
        self.bind("<Configure>", lambda _event: self._paint())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)
        self._paint()

    def set_state(self, *, selected: bool, theme: ThemeBundle) -> None:
        self._selected = selected
        self._theme = theme
        self._paint()

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._paint()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._paint()

    def _on_click(self, _event: tk.Event) -> None:
        self._on_navigate(self._nav_name)

    def _paint(self) -> None:
        ui = self._theme.ui
        width = max(1, self.winfo_width())
        height = max(self.HEIGHT, self.winfo_height())
        background = (
            ui.control_active
            if self._selected
            else ui.surface_alt if self._hovered
            else ui.control_background
        )
        border = ui.accent_primary if self._selected else ui.border
        foreground = "#ffffff" if self._selected else ui.control_text
        self.configure(bg=background, highlightbackground=border)
        self.delete("all")

        if self._selected:
            self.create_rectangle(
                0,
                0,
                5,
                height,
                fill=ui.accent_primary,
                outline="",
            )

        self.create_text(
            width / 2,
            height / 2,
            text=_NAV_LABELS.get(self._nav_name, self._nav_name),
            fill=foreground,
            font=("Sans", FONT_CONTROL, "bold"),
        )


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
        self._tiles: dict[str, _NavTile] = {}
        self.pack_propagate(False)
        self.rebuild(theme=theme, items=items, active=active)

    def rebuild(self, *, theme: ThemeBundle, items: list[str], active: str) -> None:
        ui = theme.ui
        self.configure(bg=ui.background)
        for child in self.winfo_children():
            child.destroy()
        self._tiles.clear()
        for item in items:
            tile = _NavTile(
                self,
                name=item,
                theme=theme,
                on_navigate=self._on_navigate,
            )
            tile.pack(fill=tk.X, padx=4, pady=2)
            self._tiles[item] = tile
        self.set_active(active=active, theme=theme)

    def set_active(self, *, active: str, theme: ThemeBundle) -> None:
        self.configure(bg=theme.ui.background)
        for name, tile in self._tiles.items():
            tile.set_state(selected=name == active, theme=theme)
