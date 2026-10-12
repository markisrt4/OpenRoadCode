# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic ORC tab controls without platform-native notebook styling."""

import tkinter as tk
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget


class DiagnosticsTabs(tk.Frame, UiWidget):
    """Keep Diagnostics navigation consistent with ORC shell controls."""

    def __init__(self, parent, *, theme: ThemeBundle):
        super().__init__(parent, bg=theme.ui.background)
        self._ui = theme.ui
        self._pages = []
        self._controls = tk.Frame(self, bg=self._ui.background)
        self._controls.pack(fill=tk.X, pady=(0, 6))

    def add(self, page, *, text: str) -> None:
        """Add a keyboard-focusable, theme-colored page selector."""
        index = len(self._pages)
        button = tk.Button(self._controls, text=text.upper(), command=lambda: self._select(index),
                           bg=self._ui.control_background, fg=self._ui.control_text,
                           activebackground=self._ui.control_active, activeforeground=self._ui.control_text,
                           relief=tk.FLAT, bd=0, highlightthickness=1, highlightbackground=self._ui.border,
                           font=("Sans", 10, "bold"), padx=12, pady=8, cursor="hand2", takefocus=True)
        button.pack(side=tk.LEFT, padx=(0, 5))
        self._pages.append((page, button))
        if index == 0:
            self._select(0)

    def _select(self, index: int) -> None:
        for position, (page, button) in enumerate(self._pages):
            page.pack_forget()
            button.configure(bg=self._ui.control_active if position == index else self._ui.control_background,
                             fg="#ffffff" if position == index else self._ui.control_text,
                             highlightbackground=self._ui.accent_primary if position == index else self._ui.border)
        self._pages[index][0].pack(fill=tk.BOTH, expand=True)
