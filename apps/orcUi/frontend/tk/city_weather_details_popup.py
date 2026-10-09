# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""City weather details render contract state without provider or map access."""
import tkinter as tk
from tkinter import ttk

from frontends.common.weather_overlay_format import city_time_label, weather_value
from ui.ui_widget import UiWidget


class CityWeatherDetailsPopup(tk.Toplevel, UiWidget):
    """Show a selected city's model estimates and cached hourly values."""

    def __init__(self, owner, state, *, ui, imperial, on_close):
        super().__init__(owner, bg=ui.control_background)
        self.withdraw()
        self.overrideredirect(True)
        self.transient(owner.winfo_toplevel())
        self._owner, self._imperial = owner, imperial
        body = tk.Frame(self, bg=ui.control_background, padx=12, pady=10)
        body.pack(fill=tk.BOTH, expand=True)
        header = tk.Frame(body, bg=ui.control_background)
        header.pack(fill=tk.X)
        self._title = tk.Label(header, bg=ui.control_background, fg=ui.text, font=('Sans', 12, 'bold'))
        self._title.pack(side=tk.LEFT)
        tk.Button(header, text='× Close', command=on_close, bg=ui.control_background,
                  fg=ui.text, relief=tk.FLAT, padx=8, pady=4).pack(side=tk.RIGHT)
        self._time = tk.Label(body, bg=ui.control_background, fg=ui.text_muted, anchor='w', justify=tk.LEFT, wraplength=440)
        self._time.pack(fill=tk.X, pady=3)
        self._summary = tk.Label(body, bg=ui.control_background, fg=ui.text, anchor='w', justify=tk.LEFT, wraplength=440)
        self._summary.pack(fill=tk.X, pady=4)
        self._source = tk.Label(body, bg=ui.control_background, fg=ui.text_muted, anchor='w', justify=tk.LEFT, wraplength=440)
        self._source.pack(fill=tk.X, pady=3)
        table_host = tk.Frame(body, bg=ui.control_background)
        table_host.pack(fill=tk.BOTH, expand=True)
        style = ttk.Style(self)
        style.configure('CityWeather.Treeview', background=ui.control_background,
                        fieldbackground=ui.control_background, foreground=ui.text, rowheight=24)
        style.configure('CityWeather.Treeview.Heading', background=ui.control_background,
                        foreground=ui.text)
        self._table = ttk.Treeview(table_host, style='CityWeather.Treeview', columns=('time', 'temp', 'wind', 'rain'), show='headings', height=6)
        for name, label, width in (('time', 'Local time', 145), ('temp', 'Temp', 75),
                                   ('wind', 'Wind', 90), ('rain', 'Rain / hour', 95)):
            self._table.heading(name, text=label)
            self._table.column(name, width=width, minwidth=55, anchor='w')
        self._table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(table_host, orient=tk.VERTICAL, command=self._table.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._table.configure(yscrollcommand=scroll.set)
        self.bind('<Escape>', lambda _event: on_close())
        self.render(state)
        self.update_idletasks()
        root = owner.winfo_toplevel()
        width = min(490, max(280, root.winfo_width() - 24))
        height = min(self.winfo_reqheight(), max(200, root.winfo_height() - 24))
        x = max(0, root.winfo_rootx() + (root.winfo_width() - width) // 2)
        y = max(0, root.winfo_rooty() + (root.winfo_height() - height) // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        self.deiconify()
        self.lift()

    def render(self, state):
        """Update the same popup after time selection, unit changes or refreshed data."""
        details = state.details
        if details is None:
            return
        self._title.configure(text=details.name)
        self._time.configure(text=city_time_label(state))
        def value(number, kind):
            return weather_value(number, kind, self._imperial())
        when = details.selected_at.astimezone().strftime('%a %I:%M %p %Z').replace(' 0', ' ')
        self._summary.configure(text=f"At {when}: {value(details.temperature_k, 'temperature')} · Wind {value(details.wind_speed_m_s, 'wind')}\n"
                                     f"Precipitation in selected {state.hours}h window: {value(details.precipitation_m, 'precipitation')}")
        stamp = details.fetched_at.astimezone().strftime('%I:%M %p').lstrip('0') if details.fetched_at else 'unknown'
        self._source.configure(text=f"{'Weather forecast' if state.period == 'future' else 'Recent weather estimates'} · Updated {stamp}\n— means unavailable; hourly amounts cover the preceding hour\nWeather data provider: Open-Meteo")
        self._table.delete(*self._table.get_children())
        for row in details.hours:
            row_id = self._table.insert('', tk.END, values=(row.valid_at.astimezone().strftime('%a %I:%M %p').replace(' 0', ' '),
                               value(row.temperature_k, 'temperature'), value(row.wind_speed_m_s, 'wind'),
                               value(row.precipitation_m, 'precipitation')))
            if row.valid_at == details.selected_at:
                self._table.selection_set(row_id)
                self._table.see(row_id)
