# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Power-dialog presentation for the ORC shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle


class PowerDialog:
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
        self._root = root
        self._theme = theme
        self._on_exit = on_exit
        self._on_restart = on_restart
        self._on_shutdown = on_shutdown
        self._dialog: tk.Toplevel | None = None

    def show(self) -> None:
        if self._dialog is not None and self._dialog.winfo_exists():
            self._dialog.lift()
            return
        ui = self._theme().ui
        dialog = tk.Toplevel(self._root)
        self._dialog = dialog
        dialog.title("OpenRoadCode Power")
        dialog.transient(self._root)
        dialog.resizable(False, False)
        dialog.configure(bg=ui.surface)
        dialog.protocol("WM_DELETE_WINDOW", self.close)
        frame = tk.Frame(dialog, bg=ui.surface, padx=18, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text="POWER", fg=ui.text, bg=ui.surface, font=("Sans", 16, "bold")).pack(pady=(0, 4))
        tk.Label(
            frame,
            text="System actions are intentionally two taps away.",
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", 9),
        ).pack(pady=(0, 14))
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
            ).pack(fill=tk.X, pady=3)
        self._center(dialog)

    def close(self) -> None:
        dialog = self._dialog
        self._dialog = None
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()

    def _center(self, dialog: tk.Toplevel) -> None:
        dialog.update_idletasks()
        width, height = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        x = self._root.winfo_rootx() + max(0, (self._root.winfo_width() - width) // 2)
        y = self._root.winfo_rooty() + max(0, (self._root.winfo_height() - height) // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
