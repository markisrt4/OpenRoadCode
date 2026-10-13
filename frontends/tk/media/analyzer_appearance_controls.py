# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Compact presentation controls for the frequency analyzer."""
from dataclasses import replace
import tkinter as tk
from tkinter import colorchooser

from ui.ui_widget import UiWidget
from ui.music_visualizer.music_visualizer_types import AnalyzerAppearance, AnalyzerPalette


class AnalyzerAppearanceControls(tk.Frame, UiWidget):
    """Emit immutable appearance requests; owns no capture or analysis services."""

    def __init__(self, parent, *, ui, appearance, on_change):
        super().__init__(parent, bg=ui.surface)
        self._ui, self._appearance, self._on_change = ui, appearance, on_change
        self._tab = 'LOOK'
        self._buttons = {}
        tabs = tk.Frame(self, bg=ui.surface)
        tabs.pack(fill=tk.X)
        for index, name in enumerate(('LOOK', 'COLOR', 'MOTION')):
            label = {'MOTION': 'MOVE', 'LABELS': 'TEXT'}.get(name, name)
            button = self._button(tabs, label, lambda n=name: self._show(n))
            tabs.columnconfigure(index, weight=1, uniform='appearance')
            button.grid(row=0, column=index, sticky='ew', padx=1)
            self._buttons[name] = button
        self._body = tk.Frame(self, bg=ui.surface)
        self._body.pack(fill=tk.X)
        self._show('LOOK')

    def _button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=self._ui.control_background,
                         fg=self._ui.control_text, activebackground=self._ui.control_active,
                         relief=tk.FLAT, bd=0, font=('Sans', 7, 'bold'), padx=1, pady=3)

    def _change(self, **changes):
        self._appearance = replace(self._appearance, **changes)
        self._on_change(self._appearance)

    def _toggle(self, text, field):
        value = tk.BooleanVar(value=getattr(self._appearance, field))
        button = tk.Checkbutton(self._body, text=text, variable=value,
                               command=lambda: self._change(**{field: value.get()}),
                               bg=self._ui.surface, fg=self._ui.text, anchor='w',
                               selectcolor=self._ui.control_background,
                               activebackground=self._ui.surface, activeforeground=self._ui.text,
                               font=('Sans', 9), pady=0, bd=0)
        button.pack(fill=tk.X)

    def _slider(self, title, field, low, high, increment, *, width_percent=False, bar_density=False):
        initial = getattr(self._appearance, field)
        value = tk.DoubleVar(value=(72-initial)/8 if bar_density else (1-initial)*100 if width_percent else initial)
        header = tk.Frame(self._body, bg=self._ui.surface)
        header.pack(fill=tk.X)
        tk.Label(header, text=title, bg=self._ui.surface, fg=self._ui.text,
                 font=('Sans', 7)).pack(side=tk.LEFT)
        tk.Label(header, textvariable=value, bg=self._ui.surface, fg=self._ui.text,
                 font=('Sans', 7)).pack(side=tk.RIGHT)
        row = tk.Frame(self._body, bg=self._ui.surface)
        row.pack(fill=tk.X)

        def update(number):
            self._change(**{field: int(72-float(number)*8) if bar_density else
                           round(1-float(number)/100, 6) if width_percent else float(number)})

        def step(delta):
            number = round(max(low, min(high, value.get()+delta)), 2)
            value.set(number)
            update(number)

        for text, delta, side in (('-', -increment, tk.LEFT), ('+', increment, tk.RIGHT)):
            button = self._button(row, text, lambda d=delta: step(d))
            button.configure(width=3, font=('Sans', 11, 'bold'), padx=4, pady=1)
            button.pack(side=side)
        tk.Scale(row, variable=value, from_=low, to=high, resolution=increment,
                 command=update, orient=tk.HORIZONTAL, showvalue=False, length=70,
                 bg=self._ui.surface, troughcolor=self._ui.control_background,
                 activebackground=self._ui.accent_primary, highlightthickness=0,
                 sliderlength=20, bd=0).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _choose_color(self, field):
        rgb = getattr(self._appearance, field)
        initial = '#'+''.join(f'{round(channel*255):02x}' for channel in rgb)
        color, _hex = colorchooser.askcolor(initial, parent=self, title='Analyzer gradient color')
        if color is not None:
            self._change(palette=AnalyzerPalette.CUSTOM,
                         **{field: tuple(channel/255 for channel in color)})
            self._show('COLOR')

    def _reset(self):
        self._appearance = AnalyzerAppearance()
        self._on_change(self._appearance)
        self._show(self._tab)

    def _show(self, name):
        self._tab = name
        for child in self._body.winfo_children():
            child.destroy()
        for tab, button in self._buttons.items():
            button.configure(bg=self._ui.accent_primary if tab == name else self._ui.control_background)
        if name == 'LOOK':
            self._toggle('Segmented bars', 'segmented')
            self._toggle('Peak markers', 'peak_markers')
            self._slider('BAR WIDTH: NARROW - WIDE', 'band_count', 1, 8, 1, bar_density=True)
        elif name == 'COLOR':
            value = tk.StringVar(value=self._appearance.palette.value)
            menu = tk.OptionMenu(self._body, value, *(p.value for p in AnalyzerPalette),
                                 command=lambda v: self._change(palette=AnalyzerPalette(v)))
            menu.configure(bg=self._ui.control_background, fg=self._ui.control_text,
                           activebackground=self._ui.control_active, relief=tk.FLAT,
                           highlightthickness=0, font=('Sans', 9))
            menu['menu'].configure(bg=self._ui.surface, fg=self._ui.text,
                                   activebackground=self._ui.control_active)
            menu.pack(fill=tk.X)
            colors = tk.Frame(self._body, bg=self._ui.surface)
            colors.pack(fill=tk.X)
            for title, field in (('BASE COLOR', 'low_color'), ('TIP COLOR', 'high_color')):
                button = self._button(colors, title, lambda f=field: self._choose_color(f))
                rgb = getattr(self._appearance, field)
                button.configure(highlightthickness=2,
                                 highlightbackground='#'+''.join(f'{round(c*255):02x}' for c in rgb))
                button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        elif name == 'MOTION':
            self._slider('RISE TIME (s)', 'response_s', 0, .3, .05)
            self._slider('DECAY TIME (s)', 'decay_s', .1, 1.5, .1)
        self._button(self._body, 'RESET APPEARANCE', self._reset).pack(fill=tk.X, pady=(2, 0))
        self.event_generate('<<AppearanceLayoutChanged>>')
