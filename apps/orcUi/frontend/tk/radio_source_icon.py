# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radio source icon drawing for the orcUi radio chooser."""

from __future__ import annotations

import tkinter as tk

from ui.theme import ThemeBundle


def draw_source_icon(
    canvas: tk.Canvas,
    *,
    icon_kind: str,
    accent: str,
    theme: ThemeBundle,
) -> None:
    """Draw the RF or streaming source icon."""
    ui = theme.ui
    canvas.create_oval(5, 5, 59, 59, outline=accent, width=2)
    if icon_kind == "rf":
        canvas.create_line(32, 47, 32, 28, fill=ui.text, width=3)
        canvas.create_oval(28, 24, 36, 32, fill=accent, outline=accent)
        canvas.create_arc(19, 15, 45, 41, start=310, extent=100, style=tk.ARC, outline=accent, width=2)
        canvas.create_arc(12, 8, 52, 48, start=310, extent=100, style=tk.ARC, outline=ui.text_muted, width=2)
        canvas.create_line(23, 51, 41, 51, fill=ui.text_muted, width=2)
        return

    canvas.create_oval(27, 27, 37, 37, fill=accent, outline=accent)
    canvas.create_arc(20, 20, 44, 44, start=315, extent=90, style=tk.ARC, outline=accent, width=2)
    canvas.create_arc(13, 13, 51, 51, start=315, extent=90, style=tk.ARC, outline=ui.text_muted, width=2)
    canvas.create_arc(7, 7, 57, 57, start=315, extent=90, style=tk.ARC, outline=accent, width=2)
