# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tkinter presentation adapter for frontend-neutral button help."""

from __future__ import annotations

import tkinter as tk

from ui.button_help import ButtonHelp


class HoverHelp:
    """Show delayed contextual help for a Tkinter widget."""

    def __init__(self, widget: tk.Widget, help_info: ButtonHelp) -> None:
        self._widget = widget
        self._help = help_info
        self._after_id: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _event=None) -> None:
        self._cancel_pending()
        self._after_id = self._widget.after(self._help.delay_ms, self._show)

    def _on_leave(self, _event=None) -> None:
        self._cancel_pending()
        self._hide()

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            self._widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        if self._window is not None or not self._widget.winfo_exists():
            return
        x = self._widget.winfo_rootx() + self._widget.winfo_width() + 8
        y = self._widget.winfo_rooty() + 2
        window = tk.Toplevel(self._widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            window,
            text=self._help.text,
            bg="#101820",
            fg="#edf2f5",
            relief=tk.SOLID,
            borderwidth=1,
            padx=7,
            pady=4,
            font=("Sans", 8),
            justify=tk.LEFT,
        ).pack()
        self._window = window

    def _hide(self) -> None:
        if self._window is not None:
            self._window.destroy()
            self._window = None
