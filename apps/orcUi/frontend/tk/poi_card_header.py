# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Theme-colored POI identity header, with a restrained vertical gradient."""
import base64
import tkinter as tk

from ui.ui_widget import UiWidget
from ui.navigation.poi_models import PoiIcon
from ui.theme.ui_theme import UiTheme


class PoiCardHeader(tk.Canvas, UiWidget):
    """Display supplied identity/image data without discovering business assets."""

    def __init__(self, parent, *, title: str, details: str, icon: PoiIcon | None, theme: UiTheme):
        self._title, self._details, self._theme = title, details, theme
        self._poi_icon = None
        super().__init__(parent, height=96, bg=theme.surface_alt, highlightthickness=0, bd=0)
        if icon is not None and icon.media_type == 'image/png':
            try:
                self._poi_icon = tk.PhotoImage(master=self, data=base64.b64encode(icon.data))
            except tk.TclError:
                pass
        self.bind('<Configure>', lambda _event: self._draw())
        self.bind('<Destroy>', lambda _event: setattr(self, '_poi_icon', None))

    def _blend(self, first, second, amount):
        left, right = self.winfo_rgb(first), self.winfo_rgb(second)
        return '#' + ''.join(f'{round((a + (b - a) * amount) / 257):02x}' for a, b in zip(left, right))

    def _draw(self):
        self.delete('all')
        width, height = self.winfo_width(), self.winfo_height()
        top = self._blend(self._theme.surface_alt, self._theme.accent_primary, .22)
        for index in range(32):
            color = self._blend(top, self._theme.surface_alt, index / 31)
            self.create_rectangle(0, height * index / 32, width, height * (index + 1) / 32 + 1,
                                  fill=color, outline='', tags='gradient')
        x = 22
        if self._poi_icon is not None:
            self.create_image(48, height / 2, image=self._poi_icon, tags='business-icon')
            x = 94
        self.create_text(x, 17, text='PLACE DETAILS', anchor='w', fill=self._theme.accent_primary,
                         font=('Sans', 8, 'bold'))
        title = self.create_text(x, 31, text=self._title, anchor='nw', width=max(80, width - x - 20),
                                 fill=self._theme.text, font=('Sans', 16, 'bold'))
        bounds = self.bbox(title)
        details_y = max(64, bounds[3] + 6 if bounds else 64)
        details = self.create_text(x, details_y, text=self._details, anchor='nw',
            width=max(80, width - x - 20), fill=self._theme.text_muted, font=('Sans', 10))
        bounds = self.bbox(details)
        needed = max(96, bounds[3] + 12 if bounds else 96)
        if int(self.cget('height')) != needed:
            self.configure(height=needed)
