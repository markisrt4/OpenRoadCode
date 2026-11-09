# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Compact ordering-app availability and explicit store shortcut."""
import base64
import tkinter as tk

from ui.ui_widget import UiWidget
from ui.navigation.poi_models import PoiAppAvailability


class PoiAppIndicator(tk.Canvas, UiWidget):
    """Draw supplied app state; emit only the supplied store request."""

    def __init__(self, parent, *, icon, theme, open_store):
        super().__init__(parent, width=54, height=48, bg=theme.surface_alt,
                         highlightthickness=1, highlightbackground=theme.border,
                         takefocus=True, bd=0)
        self._theme = theme
        self._open_store = open_store
        self._availability = PoiAppAvailability.UNKNOWN
        self._enabled = True
        self._icon = None
        if icon is not None and icon.media_type == 'image/png':
            try:
                self._icon = tk.PhotoImage(master=self, data=base64.b64encode(icon.data)).subsample(2)
            except tk.TclError:
                pass
        self.bind('<Button-1>', lambda _event: self.invoke())
        self.bind('<Return>', lambda _event: self.invoke())
        self.bind('<space>', lambda _event: self.invoke())
        self.bind('<Destroy>', lambda _event: setattr(self, '_icon', None))
        self.set_availability(PoiAppAvailability.UNKNOWN)

    def set_enabled(self, enabled):
        self._enabled = enabled
        self.configure(cursor='hand2' if enabled and self._availability is PoiAppAvailability.NOT_INSTALLED else '')

    def invoke(self):
        if self._enabled and self._availability is PoiAppAvailability.NOT_INSTALLED:
            self._open_store()

    def set_availability(self, availability):
        self._availability = availability
        self.delete('all')
        color = self._theme.text_muted
        if availability is PoiAppAvailability.NOT_INSTALLED:
            # Play's four-color triangle with an explicit download badge.
            self.create_polygon(12, 8, 30, 24, 12, 40, fill='#00c4ff', outline='')
            self.create_polygon(12, 8, 35, 20, 30, 24, fill='#00d26a', outline='')
            self.create_polygon(30, 24, 35, 20, 42, 24, 35, 28, fill='#ffcf00', outline='')
            self.create_polygon(12, 40, 30, 24, 35, 28, fill='#ff384b', outline='')
            self.create_oval(34, 30, 53, 48, fill=self._theme.surface_alt, outline=color)
            self.create_line(43, 33, 43, 42, fill=color, width=2, arrow=tk.LAST)
        elif availability is PoiAppAvailability.INSTALLED:
            if self._icon is not None:
                self.create_image(24, 24, image=self._icon)
            else:
                self.create_rectangle(14, 8, 34, 39, outline=color, width=2)
            self.create_oval(33, 29, 53, 48, fill=self._theme.surface_alt, outline=self._theme.accent_success)
            self.create_line(37, 38, 41, 42, 49, 34, fill=self._theme.accent_success, width=2)
        elif availability is PoiAppAvailability.WEB_ONLY:
            self.create_oval(12, 9, 42, 39, outline=color, width=2)
            self.create_oval(21, 9, 33, 39, outline=color)
            self.create_line(12, 24, 42, 24, fill=color)
        else:
            self.create_rectangle(14, 7, 38, 41, outline=color, width=2)
            self.create_text(26, 24, text='?', fill=color, font=('Sans', 16, 'bold'))
        self.set_enabled(self._enabled)
