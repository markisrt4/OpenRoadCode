# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact manual-transmission shifter gauge for Tk automotive frontends."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk

from ui.theme import StyleSheet


@dataclass(frozen=True, slots=True)
class ShifterTheme:
    """Resolved visual values used by :class:`ShifterGauge`."""

    background: str
    panel: str
    border: str
    text: str
    muted: str
    active: str
    selected_background: str

    @classmethod
    def from_style_sheet(cls, sheet: StyleSheet) -> "ShifterTheme":
        values = sheet.declarations(".automotive-shifter")
        root = sheet.declarations(":root")
        return cls(
            background=values.get("background", root["--background"]),
            panel=values.get("--panel", values.get("background", root["--surface"])),
            border=values.get("--border", root["--border"]),
            text=values.get("color", root["--text"]),
            muted=values.get("--gear-inactive", root["--text-muted"]),
            active=values.get("--gear-active", root["--accent-danger"]),
            selected_background=values.get("--gear-selected-background", root["--surface-alt"]),
        )


class ShifterGauge(tk.Canvas):
    """Show the current gear beside a compact Veloster six-speed pattern."""

    VALID_GEARS = {"R", "N", "1", "2", "3", "4", "5", "6"}

    def __init__(
        self,
        parent: tk.Misc,
        *,
        width: int = 330,
        height: int = 58,
        theme: ShifterTheme | None = None,
    ) -> None:
        self._theme = theme or ShifterTheme(
            background="#090a0b",
            panel="#111315",
            border="#626668",
            text="#d9dbd9",
            muted="#747879",
            active="#ff3143",
            selected_background="#57131b",
        )
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=self._theme.background,
            highlightthickness=0,
            bd=0,
        )
        self._gear: str | None = None
        self.bind("<Configure>", lambda _event: self._draw())
        self.after_idle(self._draw)

    def set_theme(self, theme: ShifterTheme) -> None:
        """Apply a resolved theme and repaint all canvas primitives."""

        self._theme = theme
        self.configure(bg=theme.background)
        self._draw()

    def set_style_sheet(self, sheet: StyleSheet) -> None:
        """Apply the automotive shifter rule from a parsed stylesheet."""

        self.set_theme(ShifterTheme.from_style_sheet(sheet))

    def set_gear(self, gear: str | int | None) -> None:
        if gear is None:
            self._gear = None
        else:
            value = str(gear).strip().upper()
            self._gear = value if value in self.VALID_GEARS else None
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        theme = self._theme

        pad = max(3, int(h * 0.06))
        self.create_rectangle(
            pad,
            pad,
            w - pad,
            h - pad,
            fill=theme.panel,
            outline=theme.border,
            width=1,
        )

        digital_right = w * 0.23
        self.create_text(
            digital_right * 0.46,
            h * 0.27,
            text="GEAR",
            fill=theme.text,
            font=("DejaVu Sans Condensed", max(7, int(h * 0.12)), "bold"),
        )
        self.create_text(
            digital_right * 0.46,
            h * 0.65,
            text=self._gear or "—",
            fill=theme.active,
            font=("DejaVu Sans Mono", max(18, int(h * 0.34)), "bold"),
        )
        self.create_line(
            digital_right,
            pad * 1.5,
            digital_right,
            h - pad * 1.5,
            fill=theme.border,
            width=1,
        )

        x_positions = [w * 0.40, w * 0.56, w * 0.70, w * 0.84]
        top_y = h * 0.31
        bottom_y = h * 0.70
        mid_y = (top_y + bottom_y) / 2

        for x in x_positions[1:]:
            self.create_line(x, top_y, x, bottom_y, fill=theme.muted, width=2)
        self.create_line(x_positions[1], mid_y, x_positions[3], mid_y, fill=theme.muted, width=2)
        self.create_line(x_positions[0], top_y, x_positions[1], top_y, fill=theme.muted, width=2)

        positions = {
            "R": (x_positions[0], top_y),
            "1": (x_positions[1], top_y),
            "2": (x_positions[1], bottom_y),
            "3": (x_positions[2], top_y),
            "4": (x_positions[2], bottom_y),
            "5": (x_positions[3], top_y),
            "6": (x_positions[3], bottom_y),
        }
        for gear, (x, y) in positions.items():
            selected = self._gear == gear
            if selected:
                radius = max(6, h * 0.10)
                self.create_oval(
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius,
                    fill=theme.selected_background,
                    outline=theme.active,
                    width=1,
                )
            self.create_text(
                x,
                y,
                text=gear,
                fill=theme.active if selected else theme.text,
                font=("DejaVu Sans", max(8, int(h * 0.14)), "bold"),
            )

        neutral_x = (x_positions[1] + x_positions[2]) / 2
        if self._gear == "N":
            radius = max(3, h * 0.045)
            self.create_oval(
                neutral_x - radius,
                mid_y - radius,
                neutral_x + radius,
                mid_y + radius,
                fill=theme.active,
                outline="",
            )
