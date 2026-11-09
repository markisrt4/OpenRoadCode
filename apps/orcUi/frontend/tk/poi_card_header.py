# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Theme-colored POI identity header, with a restrained vertical gradient."""
import base64
import tkinter as tk
from tkinter import font as tkfont

from ui.ui_widget import UiWidget
from ui.navigation.poi_models import PoiIcon, PoiTitleStyle
from ui.theme.ui_theme import UiTheme


class PoiCardHeader(tk.Canvas, UiWidget):
    """Display supplied identity/image data without discovering business assets."""

    def __init__(self, parent, *, title: str, details: str, icon: PoiIcon | None, theme: UiTheme,
                 title_style: PoiTitleStyle | None = None):
        self._title, self._details, self._theme = title, details, theme
        self._poi_icon = None
        super().__init__(parent, height=88, bg=theme.surface_alt, highlightthickness=0, bd=0)
        available = {family.casefold(): family for family in tkfont.families(self)}
        preferred = title_style.font_families if title_style is not None else ('Sans',)
        self._title_family = next((available[family.casefold()] for family in (*preferred, 'Helvetica', 'Arial')
                                   if family.casefold() in available), 'Sans')
        self._title_color = title_style.color if title_style is not None else theme.text
        try:
            self.winfo_rgb(self._title_color)
        except tk.TclError:
            self._title_color = theme.text
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
        top = self._blend(self._theme.surface_alt, self._theme.accent_primary, .32)
        for index in range(32):
            color = self._blend(top, self._theme.surface_alt, index / 31)
            self.create_rectangle(0, height * index / 32, width, height * (index + 1) / 32 + 1,
                                  fill=color, outline='', tags='gradient')
        x = 22
        if self._poi_icon is not None:
            self.create_image(48, height / 2, image=self._poi_icon, tags='business-icon')
            x = 94
        title = self.create_text(x, 21, text=self._title, anchor='nw', width=max(80, width - x - 20),
                                 fill=self._title_color, font=(self._title_family, 18, 'bold'), tags='poi-title')
        bounds = self.bbox(title)
        if bounds and self._contrast(self._title_color, top) < 4.5:
            chip = max(('#ffffff', '#101820'), key=lambda color: self._contrast(self._title_color, color))
            background = self.create_rectangle(bounds[0] - 5, bounds[1] - 3, bounds[2] + 5, bounds[3] + 3,
                                                fill=chip, outline='', tags='title-contrast')
            self.tag_lower(background, title)
        details_y = max(57, bounds[3] + 8 if bounds else 57)
        details = self.create_text(x, details_y, text=self._details, anchor='nw',
            width=max(80, width - x - 20), fill=self._theme.text_muted, font=('Sans', 10))
        bounds = self.bbox(details)
        needed = max(88, bounds[3] + 12 if bounds else 88)
        if int(self.cget('height')) != needed:
            self.configure(height=needed)

    def _contrast(self, first, second):
        def luminance(color):
            values = [value / 65535 for value in self.winfo_rgb(color)]
            values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
            return sum(value * weight for value, weight in zip(values, (.2126, .7152, .0722)))
        left, right = sorted((luminance(first), luminance(second)))
        return (right + .05) / (left + .05)
