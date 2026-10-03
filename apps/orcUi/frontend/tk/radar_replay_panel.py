# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact radar timeline displayed above an embedded native map window."""

from datetime import datetime
import tkinter as tk

from .shell_metrics import FONT_CONTROL


class RadarReplayPanel(tk.Toplevel):
    """Keep replay controls together in a collapsible floating panel."""

    def __init__(self, owner, anchor, *, on_play, on_seek, on_live, on_close,
                 on_palette, classic, on_speed, speed_value, ui, on_source=None):
        super().__init__(owner, bg=ui.control_background)
        self.withdraw()
        self.overrideredirect(True)
        self.transient(owner.winfo_toplevel())
        self._frame_index = None
        self._on_seek = on_seek
        self._times = ()
        self._anchor = anchor
        self._ui = ui
        self._body = tk.Frame(self, bg=ui.control_background, padx=12, pady=8)
        self._body.pack(fill=tk.BOTH, expand=True)
        title = self._row()
        self._title = self._label(title, "Radar history")
        self._title.pack(side=tk.LEFT)
        self._button(title, "×", on_close).pack(side=tk.RIGHT)
        self._timestamp = self._label(self._body, "Turn radar on to load history")
        self._timestamp.pack(anchor="w", pady=(3, 0))
        self._value = tk.IntVar(self, value=0)
        self._timeline = tk.Scale(
            self._body, from_=0, to=1, orient=tk.HORIZONTAL, showvalue=False,
            variable=self._value, command=self._scrub, resolution=1,
            bg=ui.control_background, fg=ui.control_text, troughcolor=ui.background,
            highlightthickness=0, length=270, sliderlength=28, width=18,
        )
        self._timeline.pack(fill=tk.X, pady=4)
        labels = self._row()
        self._oldest = self._label(labels, "Earlier")
        self._oldest.pack(side=tk.LEFT)
        self._edge = self._label(labels, "Latest")
        self._edge.pack(side=tk.RIGHT)
        actions = self._row()
        self._play = self._button(actions, "▶ Play", on_play)
        self._play.pack(side=tk.LEFT, pady=6)
        self._live = self._button(actions, "Live", on_live)
        self._live.pack(side=tk.RIGHT, pady=6)
        options = tk.Menubutton(actions, text="Options", bg=ui.control_background,
                                fg=ui.control_text, relief=tk.FLAT, padx=8,
                                font=("Sans", FONT_CONTROL))
        menu = tk.Menu(options, tearoff=False)
        speed = tk.StringVar(self, value=f"{speed_value:g}×")
        for text, factor in (("0.5×", 0.5), ("1×", 1.0), ("2×", 2.0)):
            menu.add_radiobutton(label=f"Playback speed {text}", variable=speed, value=text,
                                 command=lambda f=factor: on_speed(f))
        options.configure(menu=menu)
        options.pack(side=tk.RIGHT, padx=4)
        palette = self._row()
        self._classic = tk.BooleanVar(self, value=classic)
        self._classic_toggle = tk.Checkbutton(
            palette, text="Classic colors", variable=self._classic,
            command=lambda: on_palette(self._classic.get()),
            bg=ui.control_background, fg=ui.control_text,
            activebackground=ui.control_background, activeforeground=ui.control_text,
            selectcolor=ui.background, font=("Sans", FONT_CONTROL),
            highlightthickness=0, pady=5,
        )
        self._classic_toggle.pack(anchor="w")
        self._forecast = tk.BooleanVar(self, value=False)
        self._forecast_toggle = tk.Checkbutton(
            self._body, text="Forecast radar (experimental)", variable=self._forecast,
            command=lambda: on_source(self._forecast.get()),
            bg=ui.control_background, fg=ui.control_text, selectcolor=ui.background,
            activebackground=ui.control_background, activeforeground=ui.control_text,
            font=("Sans", FONT_CONTROL), highlightthickness=0, pady=5,
            state=tk.NORMAL if on_source is not None else tk.DISABLED,
        )
        self._forecast_toggle.pack(anchor="w")
        tk.Label(
            self._body, text="Contiguous United States only",
            bg=ui.control_background, fg=ui.control_text, font=("Sans", FONT_CONTROL),
        ).pack(anchor="w")
        self.bind("<Escape>", lambda _event: on_close())
        self.update_idletasks()
        self.reposition()
        self.deiconify()
        self.lift()

    def _row(self):
        row = tk.Frame(self._body, bg=self._ui.control_background)
        row.pack(fill=tk.X)
        return row

    def _label(self, parent, text):
        return tk.Label(parent, text=text, bg=self._ui.control_background,
                        fg=self._ui.control_text, font=("Sans", FONT_CONTROL))

    def _button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, relief=tk.FLAT,
                         bg=self._ui.control_active, fg=self._ui.control_text,
                         font=("Sans", FONT_CONTROL, "bold"), padx=10, pady=5)

    def reposition(self):
        """Keep the popup below the radar menu and inside the screen."""
        x = self._anchor.winfo_rootx() + self._anchor.winfo_width() - self.winfo_reqwidth()
        y = self._anchor.winfo_rooty() + self._anchor.winfo_height() + 4
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _scrub(self, value):
        index = int(float(value))
        # Updating the slider for playback must not trigger another selection.
        if self._times and index != self._frame_index:
            self._on_seek(index)

    def render(self, times, index, *, enabled, playing, forecast=False, loading=False):
        """Synchronize controls without treating playback as user scrubbing."""
        self._times = times
        self._forecast.set(forecast)
        self._title.configure(text="Forecast radar" if forecast else "Radar history")
        edge = (datetime.fromtimestamp(times[-1]).strftime("%I:%M %p").lstrip("0")
                if forecast and times else "Latest")
        self._edge.configure(text=edge)
        self._frame_index = index
        available = enabled and bool(times)
        self._timeline.configure(to=max(1, len(times) - 1),
                                 state=tk.NORMAL if available and len(times) > 1 else tk.DISABLED)
        if index is not None:
            self._value.set(index)
        self._play.configure(text="Ⅱ Pause" if playing else "▶ Play",
                             state=tk.NORMAL if available and len(times) > 1 else tk.DISABLED)
        self._live.configure(text="Now" if forecast else "Live",
                             state=tk.NORMAL if enabled or forecast else tk.DISABLED)
        if not enabled:
            label = "Turn radar on to load history"
        elif not times or index is None:
            label = "Loading radar history…"
        else:
            frame = datetime.fromtimestamp(times[index]).astimezone()
            delta = int((times[index] - datetime.now().timestamp()) / 60)
            suffix = (f"Forecast · +{max(0, delta)} min" if forecast else
                      ("Latest" if index == len(times) - 1 else f"{max(0, -delta)} min ago"))
            label = f"{frame.strftime('%I:%M %p').lstrip('0')} · {suffix}"
            if loading:
                label += " · Loading…"
        self._timestamp.configure(text=label)
        if times:
            self._oldest.configure(text=datetime.fromtimestamp(times[0]).strftime("%I:%M %p").lstrip("0"))
