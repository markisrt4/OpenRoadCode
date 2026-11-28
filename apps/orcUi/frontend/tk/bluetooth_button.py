# SPDX-License-Identifier: MIT
"""Top-bar Bluetooth shortcut with a connection-colored icon."""

import tkinter as tk
from collections.abc import Callable

from ui.ui_widget import UiWidget

from .shell_metrics import FONT_STATUS


class BluetoothButton(tk.Button, UiWidget):
    def __init__(self, parent: tk.Misc, *, background: str, active_background: str) -> None:
        super().__init__(
            parent, text="BT", bg=background, activebackground=active_background,
            compound=tk.LEFT, relief=tk.FLAT, bd=0, padx=5, pady=5,
            font=("Sans", FONT_STATUS), state=tk.DISABLED,
        )
        self._color = ""
        self._icon: tk.PhotoImage | None = None

    def set_action(self, action: Callable[[], None] | None) -> None:
        self.configure(
            command=action or "", state=tk.NORMAL if action else tk.DISABLED,
            cursor="hand2" if action else "",
        )

    def set_color(self, color: str) -> None:
        if color == self._color:
            return
        icon = tk.PhotoImage(master=self, width=15, height=19)
        icon.put(color, to=(7, 2, 9, 17))
        for offset in range(5):
            for x, y in (
                (7 + offset, 2 + offset), (11 - offset, 6 + offset),
                (7 + offset, 16 - offset), (11 - offset, 12 - offset),
                (3 + offset, 6 + offset), (3 + offset, 12 - offset),
            ):
                icon.put(color, to=(x, y, x + 2, y + 1))
        self._icon = icon
        self._color = color
        self.configure(image=icon, fg=color, activeforeground=color, disabledforeground=color)
