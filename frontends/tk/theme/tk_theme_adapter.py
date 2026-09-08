# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Apply semantic theme values to ordinary Tk widgets.

Canvas-based components remain responsible for redrawing themselves from their
own explicit theme state. This adapter intentionally does not rewrite colors
already painted into Canvas items.
"""

from __future__ import annotations

import tkinter as tk

from ui.theme import UiTheme


def apply_tk_theme(root: tk.Misc, theme: UiTheme) -> None:
    """Apply *theme* recursively to ordinary Tk widgets."""

    _apply_widget(root, theme)


def _apply_widget(widget: tk.Misc, theme: UiTheme) -> None:
    options = _options_for(widget, theme)
    if options:
        try:
            widget.configure(**options)
        except tk.TclError:
            _apply_supported_options(widget, options)

    for child in widget.winfo_children():
        _apply_widget(child, theme)


def _options_for(widget: tk.Misc, theme: UiTheme) -> dict[str, str | int]:
    if isinstance(widget, tk.Button):
        return {
            "background": theme.control_background,
            "foreground": theme.control_text,
            "activebackground": theme.control_active,
            "activeforeground": theme.control_text,
            "highlightbackground": theme.border,
        }
    if isinstance(widget, (tk.Entry, tk.Text)):
        return {
            "background": theme.surface,
            "foreground": theme.text,
            "insertbackground": theme.text,
            "highlightbackground": theme.border,
            "selectbackground": theme.accent_primary,
            "selectforeground": theme.control_text,
        }
    if isinstance(widget, tk.Label):
        return {"background": theme.background, "foreground": theme.text}
    if isinstance(widget, tk.Canvas):
        return {"background": theme.background, "highlightthickness": 0}
    if isinstance(widget, (tk.Frame, tk.Toplevel)):
        return {"background": theme.background}
    return {}


def _apply_supported_options(widget: tk.Misc, options: dict[str, str | int]) -> None:
    for name, value in options.items():
        try:
            widget.configure(**{name: value})
        except tk.TclError:
            pass
