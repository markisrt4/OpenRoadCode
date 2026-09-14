# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable shell chrome builders for the integrated orcUi window."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle


def build_top_bar(
    root: tk.Misc,
    *,
    theme: ThemeBundle,
    on_power: Callable[[], None],
) -> tk.Label:
    """Build the branded top bar and return its clock label."""
    ui = theme.ui
    bar = tk.Frame(root, bg=ui.surface_alt, height=50)
    bar.grid(row=0, column=0, columnspan=2, sticky="ew")
    bar.grid_propagate(False)
    bar.grid_columnconfigure(1, weight=1)

    brand = tk.Frame(bar, bg=ui.surface_alt)
    brand.grid(row=0, column=0, sticky="w", padx=(10, 8))
    _build_logo_mark(brand, theme)
    for letter, color in (
        ("O", ui.accent_primary),
        ("R", ui.accent_danger),
        ("C", ui.accent_success),
    ):
        tk.Label(
            brand,
            text=letter,
            fg=color,
            bg=ui.surface_alt,
            font=("Sans", 21, "bold"),
            padx=0,
            pady=0,
            bd=0,
        ).pack(side=tk.LEFT)
    tk.Label(
        brand,
        text="ui",
        fg=ui.text_muted,
        bg=ui.surface_alt,
        font=("Monospace", 12),
        padx=0,
    ).pack(side=tk.LEFT, padx=(3, 0), pady=(5, 0))

    clock = tk.Label(
        bar,
        fg=ui.text,
        bg=ui.surface_alt,
        font=("Sans", 17, "bold"),
    )
    clock.grid(row=0, column=1)

    status = tk.Frame(bar, bg=ui.surface_alt)
    status.grid(row=0, column=2, padx=(8, 14), sticky="e")
    tk.Label(
        status,
        text="☁  --°F",
        fg=ui.text,
        bg=ui.surface_alt,
        font=("Sans", 11, "bold"),
    ).pack(side=tk.LEFT, padx=(0, 10))
    tk.Label(
        status,
        text="GPS  ▮▮▮   WiFi   BT   🚗",
        fg=ui.text_muted,
        bg=ui.surface_alt,
        font=("Sans", 11),
    ).pack(side=tk.LEFT, padx=(0, 10))
    tk.Button(
        status,
        text="⏻",
        command=on_power,
        bg=ui.control_background,
        fg=ui.control_text,
        activebackground=ui.control_active,
        activeforeground="#ffffff",
        relief=tk.FLAT,
        bd=0,
        font=("Sans", 16, "bold"),
        padx=10,
        pady=2,
    ).pack(side=tk.LEFT)
    return clock


def build_footer(root: tk.Misc, *, theme: ThemeBundle) -> None:
    """Build the persistent status footer."""
    ui = theme.ui
    footer = tk.Frame(root, bg=ui.surface_alt, height=25)
    footer.grid(row=3, column=0, columnspan=2, sticky="ew")
    footer.grid_propagate(False)
    footer.grid_columnconfigure(1, weight=1)
    tk.Label(
        footer,
        text="OpenRoadCode",
        fg=ui.text_muted,
        bg=ui.surface_alt,
        font=("Sans", 8),
    ).grid(row=0, column=0, padx=10)
    tk.Label(
        footer,
        text="Services: --   |   ZMQ: --",
        fg=ui.text_muted,
        bg=ui.surface_alt,
        font=("Sans", 8),
    ).grid(row=0, column=1)
    tk.Label(
        footer,
        text="orcUi prototype",
        fg=ui.text_muted,
        bg=ui.surface_alt,
        font=("Sans", 8),
    ).grid(row=0, column=2, padx=10)


def _build_logo_mark(parent: tk.Misc, theme: ThemeBundle) -> None:
    ui = theme.ui
    logo = tk.Canvas(
        parent,
        width=32,
        height=30,
        bg=ui.surface_alt,
        highlightthickness=0,
        bd=0,
    )
    logo.pack(side=tk.LEFT, padx=(0, 4))
    logo.create_line(16, 3, 3, 26, fill=ui.accent_primary, width=4)
    logo.create_line(3, 26, 29, 26, fill=ui.accent_danger, width=4)
    logo.create_line(29, 26, 16, 3, fill=ui.accent_success, width=4)
    logo.create_line(16, 9, 16, 21, fill=ui.text_muted, width=2, dash=(3, 3))
