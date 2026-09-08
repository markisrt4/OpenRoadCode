# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact manual-transmission shifter gauge for ORC UI."""

from __future__ import annotations

import tkinter as tk


class ShifterGauge(tk.Canvas):
    """Show the current gear beside a compact Veloster six-speed pattern."""

    VALID_GEARS = {"R", "N", "1", "2", "3", "4", "5", "6"}

    def __init__(self, parent: tk.Misc, *, width: int = 330, height: int = 58) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg="#090a0b",
            highlightthickness=0,
            bd=0,
        )
        self._gear: str | None = None
        self.bind("<Configure>", lambda _event: self._draw())
        self.after_idle(self._draw)

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
        border = "#626668"
        panel = "#111315"
        text = "#d9dbd9"
        muted = "#747879"
        active = "#ff3143"

        pad = max(3, int(h * 0.06))
        self.create_rectangle(
            pad,
            pad,
            w - pad,
            h - pad,
            fill=panel,
            outline=border,
            width=1,
        )

        # The digital indication is intentionally tiny compared with the
        # primary instruments. It is supporting information, not a fifth gauge.
        digital_right = w * 0.23
        self.create_text(
            digital_right * 0.46,
            h * 0.27,
            text="GEAR",
            fill=text,
            font=("DejaVu Sans Condensed", max(7, int(h * 0.12)), "bold"),
        )
        self.create_text(
            digital_right * 0.46,
            h * 0.65,
            text=self._gear or "—",
            fill=active,
            font=("DejaVu Sans Mono", max(18, int(h * 0.34)), "bold"),
        )
        self.create_line(
            digital_right,
            pad * 1.5,
            digital_right,
            h - pad * 1.5,
            fill=border,
            width=1,
        )

        # Veloster six-speed pattern: R/1/3/5 across the top, 2/4/6 below.
        x_positions = [w * 0.40, w * 0.56, w * 0.70, w * 0.84]
        top_y = h * 0.31
        bottom_y = h * 0.70
        mid_y = (top_y + bottom_y) / 2

        for x in x_positions[1:]:
            self.create_line(x, top_y, x, bottom_y, fill=muted, width=2)
        self.create_line(x_positions[1], mid_y, x_positions[3], mid_y, fill=muted, width=2)
        self.create_line(x_positions[0], top_y, x_positions[1], top_y, fill=muted, width=2)

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
                    fill="#57131b",
                    outline=active,
                    width=1,
                )
            self.create_text(
                x,
                y,
                text=gear,
                fill=active if selected else text,
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
                fill=active,
                outline="",
            )
