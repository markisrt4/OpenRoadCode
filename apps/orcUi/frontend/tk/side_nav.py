# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent left-side navigation for the integrated orcUi shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle
from .shell_metrics import FONT_CONTROL, SIDE_NAV_WIDTH


_NAV_LABELS = {"NAVIGATION": "NAV"}


def _blend(first: str, second: str, amount: float) -> str:
    """Blend two #RRGGBB colors for lightweight Tk gradients."""
    amount = max(0.0, min(1.0, amount))
    a = tuple(int(first[index:index + 2], 16) for index in (1, 3, 5))
    b = tuple(int(second[index:index + 2], 16) for index in (1, 3, 5))
    rgb = tuple(round(left + (right - left) * amount) for left, right in zip(a, b))
    return "#{:02x}{:02x}{:02x}".format(*rgb)


class _NavTile(tk.Canvas):
    """Compact navigation tile with drawn iconography and active styling."""

    HEIGHT = 50

    def __init__(
        self,
        parent: tk.Misc,
        *,
        name: str,
        theme: ThemeBundle,
        on_navigate: Callable[[str], None],
        on_swipe: Callable[[int], None] | None = None,
    ) -> None:
        self._nav_name = name
        self._theme = theme
        self._on_navigate = on_navigate
        self._on_swipe = on_swipe
        self._selected = False
        self._hovered = False
        self._press_y: int | None = None
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
        self.bind("<ButtonPress-1>", self._on_press)
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

    def _on_press(self, event: tk.Event) -> None:
        self._press_y = event.y_root

    def _on_click(self, event: tk.Event) -> None:
        press_y = self._press_y
        self._press_y = None
        if press_y is not None and self._on_swipe is not None:
            delta_y = event.y_root - press_y
            if abs(delta_y) >= 24:
                self._on_swipe(1 if delta_y < 0 else -1)
                return
        self._on_navigate(self._nav_name)

    def _paint(self) -> None:
        ui = self._theme.ui
        width = max(SIDE_NAV_WIDTH - 8, self.winfo_width())
        height = max(self.HEIGHT, self.winfo_height())

        if self._selected:
            top = _blend(ui.control_active, "#ffffff", 0.10)
            bottom = _blend(ui.control_active, "#000000", 0.12)
            border = ui.accent_primary
            label_color = "#ffffff"
            badge_fill = _blend(ui.control_active, "#000000", 0.22)
            icon_color = "#ffffff"
        elif self._hovered:
            top = _blend(ui.control_background, ui.accent_primary, 0.13)
            bottom = _blend(ui.control_background, ui.surface_alt, 0.35)
            border = _blend(ui.border, ui.accent_primary, 0.45)
            label_color = ui.control_text
            badge_fill = _blend(ui.control_background, ui.accent_primary, 0.16)
            icon_color = ui.accent_primary
        else:
            top = _blend(ui.control_background, ui.surface_alt, 0.22)
            bottom = _blend(ui.control_background, "#000000", 0.08)
            border = ui.border
            label_color = ui.control_text
            badge_fill = _blend(ui.control_background, ui.surface_alt, 0.55)
            icon_color = ui.text_muted

        self.configure(bg=bottom, highlightbackground=border)
        self.delete("all")
        self._draw_gradient(width, height, top, bottom)

        if self._selected:
            self.create_rectangle(0, 0, 4, height, fill=ui.accent_primary, outline="")

        badge_x = 20
        badge_y = height / 2
        badge_radius = 13
        self.create_oval(
            badge_x - badge_radius, badge_y - badge_radius,
            badge_x + badge_radius, badge_y + badge_radius,
            fill=badge_fill, outline=border, width=1,
        )
        self._draw_icon(self._nav_name, badge_x, badge_y, icon_color)
        self.create_text(
            38, height / 2,
            text=_NAV_LABELS.get(self._nav_name, self._nav_name),
            fill=label_color,
            font=("Sans", FONT_CONTROL - 1, "bold"),
            anchor="w",
        )

    def _draw_gradient(self, width: int, height: int, top: str, bottom: str) -> None:
        steps = 12
        step_height = height / steps
        for index in range(steps):
            color = _blend(top, bottom, index / max(1, steps - 1))
            y1 = round(index * step_height)
            y2 = round((index + 1) * step_height) + 1
            self.create_rectangle(0, y1, width, y2, fill=color, outline="")

    def _draw_icon(self, name: str, x: float, y: float, color: str) -> None:
        if name == "HOME": self._draw_home(x, y, color)
        elif name == "NAVIGATION": self._draw_navigation(x, y, color)
        elif name == "RADIO": self._draw_radio(x, y, color)
        elif name == "VEHICLE": self._draw_vehicle(x, y, color)
        elif name == "LIGHTING": self._draw_light(x, y, color)
        elif name == "GAMES": self._draw_games(x, y, color)
        elif name == "MEDIA": self._draw_media(x, y, color)
        elif name == "VISION": self._draw_vision(x, y, color)

    def _draw_home(self, x: float, y: float, color: str) -> None:
        self.create_polygon(x - 8, y - 1, x, y - 8, x + 8, y - 1, outline=color, fill="", width=2)
        self.create_rectangle(x - 6, y - 1, x + 6, y + 7, outline=color, width=2)
        self.create_rectangle(x - 2, y + 2, x + 2, y + 7, outline=color, width=1)

    def _draw_navigation(self, x: float, y: float, color: str) -> None:
        self.create_polygon(x - 7, y + 7, x - 1, y - 8, x + 8, y - 4, x + 2, y, x + 5, y + 7, x, y + 3, fill=color, outline=color)

    def _draw_radio(self, x: float, y: float, color: str) -> None:
        self.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline=color)
        self.create_arc(x - 8, y - 8, x + 8, y + 8, start=300, extent=120, style=tk.ARC, outline=color, width=2)
        self.create_arc(x - 11, y - 11, x + 11, y + 11, start=300, extent=120, style=tk.ARC, outline=color, width=1)

    def _draw_vehicle(self, x: float, y: float, color: str) -> None:
        self.create_polygon(x - 8, y + 3, x - 5, y - 4, x + 5, y - 4, x + 8, y + 3, x + 7, y + 6, x - 7, y + 6, outline=color, fill="", width=2)
        self.create_oval(x - 6, y + 4, x - 2, y + 8, fill=color, outline=color)
        self.create_oval(x + 2, y + 4, x + 6, y + 8, fill=color, outline=color)

    def _draw_light(self, x: float, y: float, color: str) -> None:
        self.create_oval(x - 4, y - 4, x + 4, y + 4, outline=color, width=2)
        for dx, dy in ((0, -10), (0, 10), (-10, 0), (10, 0), (-7, -7), (7, -7), (-7, 7), (7, 7)):
            scale = 0.55
            self.create_line(x + dx * scale, y + dy * scale, x + dx, y + dy, fill=color, width=1)

    def _draw_games(self, x: float, y: float, color: str) -> None:
        self.create_arc(x - 9, y - 5, x + 9, y + 10, start=0, extent=180, style=tk.ARC, outline=color, width=2)
        self.create_line(x - 9, y + 2, x - 7, y + 8, fill=color, width=2)
        self.create_line(x + 9, y + 2, x + 7, y + 8, fill=color, width=2)
        self.create_line(x - 5, y + 1, x - 1, y + 1, fill=color, width=2)
        self.create_line(x - 3, y - 1, x - 3, y + 3, fill=color, width=2)
        self.create_oval(x + 3, y, x + 5, y + 2, fill=color, outline=color)
        self.create_oval(x + 6, y + 3, x + 8, y + 5, fill=color, outline=color)

    def _draw_vision(self, x: float, y: float, color: str) -> None:
        self.create_oval(x - 10, y - 6, x + 10, y + 6, outline=color, width=2)
        self.create_oval(x - 4, y - 4, x + 4, y + 4, outline=color, width=2)
        self.create_oval(x - 1.5, y - 1.5, x + 1.5, y + 1.5, fill=color, outline=color)

    def _draw_media(self, x: float, y: float, color: str) -> None:
        self.create_polygon(x - 5, y - 8, x + 8, y, x - 5, y + 8, fill=color, outline=color)


class OrcUiSideNav(tk.Frame):
    """Render a fixed-size viewport over the shell's navigation destinations."""

    WIDTH = SIDE_NAV_WIDTH
    VISIBLE_ITEMS = 6
    SCROLL_HEIGHT = 22

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
        self._theme = theme
        self._items: list[str] = []
        self._active = active
        self._offset = 0
        self._tiles: dict[str, _NavTile] = {}
        self._up_button: tk.Button | None = None
        self._down_button: tk.Button | None = None
        self.pack_propagate(False)
        self.bind("<Button-4>", lambda _event: self._scroll(-1))
        self.bind("<Button-5>", lambda _event: self._scroll(1))
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        self.rebuild(theme=theme, items=items, active=active)

    def rebuild(self, *, theme: ThemeBundle, items: list[str], active: str) -> None:
        self._theme = theme
        self._items = list(items)
        self._active = active
        self._ensure_active_visible()
        self._render()

    def set_active(self, *, active: str, theme: ThemeBundle) -> None:
        self._theme = theme
        self._active = active
        old_offset = self._offset
        self._ensure_active_visible()
        if old_offset != self._offset or active not in self._tiles:
            self._render()
            return
        self.configure(bg=theme.ui.background)
        for name, tile in self._tiles.items():
            tile.set_state(selected=name == active, theme=theme)
        self._paint_scroll_buttons()

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        if event.delta:
            self._scroll(-1 if event.delta > 0 else 1)

    def _scroll(self, delta: int) -> None:
        maximum = max(0, len(self._items) - self.VISIBLE_ITEMS)
        new_offset = max(0, min(maximum, self._offset + delta))
        if new_offset == self._offset:
            return
        self._offset = new_offset
        self._render()

    def _ensure_active_visible(self) -> None:
        maximum = max(0, len(self._items) - self.VISIBLE_ITEMS)
        self._offset = max(0, min(maximum, self._offset))
        try:
            index = self._items.index(self._active)
        except ValueError:
            return
        if index < self._offset:
            self._offset = index
        elif index >= self._offset + self.VISIBLE_ITEMS:
            self._offset = index - self.VISIBLE_ITEMS + 1
        self._offset = max(0, min(maximum, self._offset))

    def _render(self) -> None:
        theme = self._theme
        self.configure(bg=theme.ui.background)
        for child in self.winfo_children():
            child.destroy()
        self._tiles.clear()

        if len(self._items) > self.VISIBLE_ITEMS:
            self._up_button = self._make_scroll_button("▲", lambda: self._scroll(-1))
            self._up_button.pack(fill=tk.X, padx=8, pady=(0, 2))
        else:
            self._up_button = None

        visible = self._items[self._offset:self._offset + self.VISIBLE_ITEMS]
        for item in visible:
            tile = _NavTile(
                self,
                name=item,
                theme=theme,
                on_navigate=self._on_navigate,
                on_swipe=self._scroll,
            )
            tile.pack(fill=tk.X, padx=4, pady=1)
            tile.set_state(selected=item == self._active, theme=theme)
            self._tiles[item] = tile

        if len(self._items) > self.VISIBLE_ITEMS:
            self._down_button = self._make_scroll_button("▼", lambda: self._scroll(1))
            self._down_button.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(2, 0))
        else:
            self._down_button = None
        self._paint_scroll_buttons()

    def _make_scroll_button(self, text: str, command: Callable[[], None]) -> tk.Button:
        return tk.Button(
            self,
            text=text,
            command=command,
            height=1,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            font=("Sans", max(8, FONT_CONTROL - 2), "bold"),
        )

    def _paint_scroll_buttons(self) -> None:
        ui = self._theme.ui
        maximum = max(0, len(self._items) - self.VISIBLE_ITEMS)
        for button, enabled in (
            (self._up_button, self._offset > 0),
            (self._down_button, self._offset < maximum),
        ):
            if button is None:
                continue
            button.configure(
                state=tk.NORMAL if enabled else tk.DISABLED,
                bg=ui.control_background,
                fg=ui.control_text if enabled else ui.text_muted,
                activebackground=ui.control_active,
                activeforeground=ui.text,
                disabledforeground=ui.text_muted,
            )
