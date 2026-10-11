# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Small theme-colored gradient controls for persistent shell chrome."""

import tkinter as tk


class GradientControl(tk.Canvas):
    """Present an injected action with mouse and keyboard activation."""

    def __init__(self, parent, *, command, bg, fg, activebackground,
                 activeforeground, font, text=""):
        self._command = command
        self._text, self._foreground = text, fg
        self._base, self._active = bg, activebackground
        self._active_foreground = activeforeground
        self._font = font
        self._hover = False
        self._state = tk.NORMAL
        super().__init__(parent, bg=bg, height=36, width=40,
                         highlightthickness=0, bd=0, takefocus=True, cursor="hand2")
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", lambda _event: self._highlight(True))
        self.bind("<Leave>", lambda _event: self._highlight(False))
        self.bind("<ButtonPress-1>", lambda _event: self.focus_set())
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())
        self.bind("<FocusIn>", lambda _event: self._draw())
        self.bind("<FocusOut>", lambda _event: self._draw())

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        for key, attr in (("text", "_text"), ("fg", "_foreground"),
                          ("state", "_state")):
            if key in kwargs:
                setattr(self, attr, kwargs.pop(key))
        result = super().configure(**kwargs) if kwargs else None
        self._draw()
        return result

    config = configure

    def invoke(self):
        """Run the assigned action only while this control is enabled."""
        if self._state != tk.DISABLED:
            return self._command()

    def _release(self, event):
        if 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.invoke()

    def _highlight(self, value):
        self._hover = value
        self._draw()

    def _draw(self):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        rgb = self.winfo_rgb(self._active if self._hover else self._base)
        for index in range(16):
            # A restrained bottom highlight fading upward into the theme surface.
            amount = 0.09 * index / 15
            color = "#" + "".join(f"{round(value / 257 + (255 - value / 257) * amount):02x}"
                                  for value in rgb)
            self.create_rectangle(0, height * index / 16, width,
                                  height * (index + 1) / 16 + 1, fill=color, outline="")
        self.create_text(width / 2, height / 2, text=self._text, font=self._font,
                         fill=self._active_foreground if self._hover else self._foreground)
        if self.focus_get() is self:
            self.create_rectangle(2, 2, width - 3, height - 3,
                                  outline=self._foreground, width=1)
