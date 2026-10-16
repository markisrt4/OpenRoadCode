# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Shared touch targets with distinct neutral, hover and selected colors."""
import tkinter as tk

from ui.ui_widget import UiWidget


class TouchButton(tk.Frame, UiWidget):
    """Fixed-height touch target with a theme-aware native Tk button."""

    def __init__(self, parent, text, command, ui, width=None):
        super().__init__(parent, bg=ui.control_background, height=50,
                         **({"width": width} if width else {}))
        self.pack_propagate(False)
        self._ui = ui
        self._selected = False
        self._hovered = False
        self._button = tk.Button(self, text=text, command=command, relief=tk.FLAT,
            bg=ui.control_background, fg=ui.control_text,
            activebackground=ui.border, activeforeground=ui.text,
            disabledforeground=ui.text_muted, font=("Sans", 14, "bold"),
            padx=8, highlightthickness=0, bd=0,
            state=tk.NORMAL if command is not None else tk.DISABLED)
        self._button.pack(fill=tk.BOTH, expand=True)
        self._button.bind("<Enter>", lambda _event: self._set_hover(True))
        self._button.bind("<Leave>", lambda _event: self._set_hover(False))

    def _set_hover(self, hovered):
        self._hovered = hovered
        self._paint_background()

    def _paint_background(self):
        enabled = self._button.cget("state") != tk.DISABLED
        selected = self._selected and enabled
        background = (self._ui.control_active if selected else self._ui.border
                      if self._hovered and enabled else self._ui.control_background)
        # Tk uses activebackground while the pointer is over the button, so it
        # must preserve the same selected/hover distinction as the resting color.
        self._button.configure(bg=background,
            activebackground=self._ui.control_active if selected else self._ui.border)

    def configure_button(self, **options):
        self._selected = options.pop("selected", self._selected)
        self._button.configure(**options)
        self._paint_background()

