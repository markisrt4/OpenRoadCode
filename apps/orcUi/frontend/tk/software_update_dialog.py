# SPDX-License-Identifier: MIT
"""Present software update consent using the ORC shell popup."""

import tkinter as tk
from collections.abc import Callable

from .error_dialog import ShellPopup


class SoftwareUpdateDialog(ShellPopup):
    """Ask for confirmation before applying the offered update."""

    def show(self, revision: str, on_accept: Callable[[], None]) -> None:
        window = self._open("OpenRoadCode update")
        ui = self._theme().ui
        tk.Label(
            window,
            text="ORC UPDATE AVAILABLE",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 16, "bold"),
        ).pack(fill=tk.X, padx=20, pady=(16, 6))
        tk.Label(
            window,
            text=f"Update to {revision} and restart ORC?",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 12),
        ).pack(fill=tk.X, padx=20, pady=(0, 12))

        def accept() -> None:
            self.dismiss()
            on_accept()

        for label, command in (("UPDATE AND RESTART", accept), ("LATER", self.dismiss)):
            tk.Button(
                window,
                text=label,
                command=command,
                relief=tk.FLAT,
                bg=ui.control_background,
                fg=ui.control_text,
                pady=8,
            ).pack(fill=tk.X, padx=20, pady=(0, 8))

        window.update_idletasks()
        width, height = window.winfo_reqwidth(), window.winfo_reqheight()
        x = self._root.winfo_rootx() + max(0, (self._root.winfo_width() - width) // 2)
        y = self._root.winfo_rooty() + max(0, (self._root.winfo_height() - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.lift()
        window.focus_set()
