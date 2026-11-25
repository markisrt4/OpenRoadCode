# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Power-dialog presentation for the ORC shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle

from .error_dialog import ShellPopup


class PowerDialog(ShellPopup):
    """Own the modal power controls without owning system power behavior."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        theme: Callable[[], ThemeBundle],
        on_exit: Callable[[], None],
        on_restart: Callable[[], None],
        on_shutdown: Callable[[], None],
    ) -> None:
        super().__init__(root, theme)
        self._on_exit = on_exit
        self._on_restart = on_restart
        self._on_shutdown = on_shutdown

    def show(self) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.lift()
            return
        ui = self._theme().ui
        dialog = self._open("OpenRoadCode Power")
        frame = tk.Frame(dialog, bg=ui.surface, padx=18, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text="POWER", fg=ui.text, bg=ui.surface, font=("Sans", 16, "bold")).pack(
            pady=(0, 4)
        )
        for text, command in (
            ("EXIT UI", self._on_exit),
            ("RESTART UI", self._on_restart),
            ("SHUT DOWN SYSTEM", self._on_shutdown),
            ("CANCEL", self.close),
        ):
            tk.Button(
                frame,
                text=text,
                command=command,
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                width=24,
                pady=8,
                font=("Sans", 10, "bold"),
                highlightthickness=0,
                bd=0,
            ).pack(fill=tk.X, pady=3)
        self._center(dialog)
        dialog.lift()
        dialog.focus_set()

    def close(self) -> None:
        self.dismiss()

    def _center(self, dialog: tk.Toplevel) -> None:
        dialog.update_idletasks()
        width, height = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        x = self._root.winfo_rootx() + max(0, (self._root.winfo_width() - width) // 2)
        y = self._root.winfo_rooty() + max(0, (self._root.winfo_height() - height) // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
