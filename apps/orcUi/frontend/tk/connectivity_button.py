# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Online-mode button with Android-style ascending signal bars."""
import tkinter as tk


class ConnectivityButton(tk.Button):
    def __init__(self, parent, *, command, background, active_background, muted):
        self._muted = muted
        self._last_status = None
        super().__init__(parent, command=command, bg=background,
                         activebackground=active_background, relief=tk.FLAT,
                         font=('Sans', 10, 'bold'), cursor='hand2', compound=tk.RIGHT,
                         padx=8, pady=5)
        self.set_status('ONLINE · CHECKING', muted, False)

    def set_status(self, text: str, color: str, connected: bool) -> None:
        status = (text, color, connected)
        if status == self._last_status:
            return
        self._last_status = status
        image = tk.PhotoImage(master=self, width=32, height=22)
        for index, height in enumerate((5, 9, 13, 17)):
            left = 3 + index * 7
            image.put(color if connected else self._muted,
                      to=(left, 20 - height, left + 5, 20))
        self._bars_image = image
        self.configure(text=text + ' ', fg=color, image=image)
