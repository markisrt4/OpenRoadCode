# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Small content helpers for the integrated orcUi shell."""

from __future__ import annotations

import tkinter as tk

from ui.theme import ThemeBundle
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL


def panel(parent: tk.Misc, title: str, accent: str, *, theme: ThemeBundle) -> tk.Frame:
    ui = theme.ui
    frame = tk.Frame(
        parent,
        bg=ui.surface,
        highlightthickness=1,
        highlightbackground=ui.border,
    )
    tk.Label(
        frame,
        text=title,
        fg=accent,
        bg=ui.surface,
        font=("Sans", FONT_CONTROL + 1, "bold"),
    ).pack(anchor="nw", padx=14, pady=(11, 4))
    return frame


def add_summary(
    parent: tk.Misc,
    primary: str,
    secondary: str,
    *,
    theme: ThemeBundle,
) -> None:
    ui = theme.ui
    tk.Label(
        parent,
        text=primary,
        fg=ui.text,
        bg=ui.surface,
        font=("Sans", FONT_BODY + 3, "bold"),
    ).pack(anchor="w", padx=16, pady=(12, 2))
    tk.Label(
        parent,
        text=secondary,
        fg=ui.text_muted,
        bg=ui.surface,
        font=("Sans", FONT_SMALL + 1),
    ).pack(anchor="w", padx=16)
