# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Touch-sized radar controls floating above the embedded native map."""

from datetime import datetime
from functools import partial
import tkinter as tk

from ui.ui_widget import UiWidget


class _TouchButton(tk.Frame, UiWidget):
    """Fixed-height touch target with a theme-aware native Tk button."""

    def __init__(self, parent, text, command, ui, width=None):
        super().__init__(parent, bg=ui.control_background, height=50,
                         **({"width": width} if width else {}))
        self.pack_propagate(False)
        self._ui = ui
        self._selected = False
        self._hovered = False
        self._button = tk.Button(self, text=text, command=command, relief=tk.FLAT,
            bg=ui.control_background, fg=ui.control_text,
            activebackground=ui.control_active, activeforeground=ui.text,
            disabledforeground=ui.text_muted, font=("Sans", 14, "bold"),
            padx=8, highlightthickness=0, bd=0,
            state=tk.NORMAL if command is not None else tk.DISABLED)
        self._button.pack(fill=tk.BOTH, expand=True)
        self._button.bind("<Enter>", lambda _event: self._set_hover(True))
        self._button.bind("<Leave>", lambda _event: self._set_hover(False))

    def _set_hover(self, hovered):
        self._hovered = hovered
        self._paint_background()

    def _paint_background(self):
        active = (self._selected or self._hovered) and self._button.cget("state") != tk.DISABLED
        self._button.configure(bg=self._ui.control_active if active else self._ui.control_background)

    def configure_button(self, **options):
        self._selected = options.pop("selected", self._selected)
        self._button.configure(**options)
        self._paint_background()


class RadarReplayPanel(tk.Toplevel, UiWidget):
    """Present existing radar requests in large, directly accessible buttons."""

    def __init__(self, owner, anchor, *, on_play, on_seek, on_live, on_close,
                 on_palette, classic, on_speed, speed_value, ui, on_source=None,
                 on_toggle=None):
        super().__init__(owner, bg=ui.control_background)
        self.withdraw()
        self.overrideredirect(True)
        self._owner_window = owner.winfo_toplevel()
        self._owner_panel = owner
        self._compact = False
        self._playing = False
        self._on_play = on_play
        self.transient(self._owner_window)
        self._frame_index = None
        self._on_seek = on_seek
        self._times = ()
        self._ui = ui
        self._on_close = on_close
        self._closed = False
        self._tab = "playback"
        self._body = tk.Frame(self, bg=ui.control_background, padx=12, pady=10)
        self._body.pack(fill=tk.BOTH, expand=True)
        self._body.grid_columnconfigure(0, weight=1)
        title = self._row(self._body, 0)
        self._label(title, "Radar controls", bold=True).pack(side=tk.LEFT)
        self._button(title, "Close  ×", on_close, width=100).pack(side=tk.RIGHT)
        summary = self._row(self._body, 1)
        self._visibility = self._button(summary, "Radar off", on_toggle, width=140)
        self._visibility.pack(side=tk.LEFT, padx=(0, 10))
        self._timestamp = self._label(summary, "Turn radar on to load history")
        self._timestamp.configure(wraplength=360, justify=tk.LEFT)
        self._timestamp.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tabs = self._row(self._body, 2)
        self._tab_buttons = {}
        for column, (key, text) in enumerate((("playback", "Playback"), ("display", "Display"))):
            tabs.grid_columnconfigure(column, weight=1, uniform="radar-tabs")
            button = self._button(tabs, text, partial(self._show_tab, key))
            button.grid(row=0, column=column, sticky="ew", padx=(0, 4) if column == 0 else (4, 0))
            self._tab_buttons[key] = button
        self._pages = {key: tk.Frame(self._body, bg=ui.control_background)
                       for key in ("playback", "display")}
        for page in self._pages.values():
            page.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
            page.grid_columnconfigure(0, weight=1)
        playback = self._pages["playback"]
        self._value = tk.IntVar(self, value=0)
        self._timeline = tk.Scale(playback, from_=0, to=1, orient=tk.HORIZONTAL,
            showvalue=False, variable=self._value, command=self._scrub, resolution=1,
            bg=ui.control_background, fg=ui.control_text, troughcolor=ui.background,
            highlightthickness=0, bd=0, sliderlength=48, width=24)
        self._timeline.grid(row=0, column=0, sticky="ew", pady=(4, 0))
        labels = self._row(playback, 1)
        self._oldest = self._label(labels, "Earlier", small=True)
        self._oldest.pack(side=tk.LEFT)
        self._edge = self._label(labels, "Latest", small=True)
        self._edge.pack(side=tk.RIGHT)
        actions = self._row(playback, 2)
        self._previous = self._button(actions, "‹ Previous", partial(self._step, -1))
        self._play = self._button(actions, "▶ Play", on_play)
        self._next = self._button(actions, "Next ›", partial(self._step, 1))
        for column, button in enumerate((self._previous, self._play, self._next)):
            actions.grid_columnconfigure(column, weight=1, uniform="radar-transport")
            button.grid(row=0, column=column, sticky="ew", padx=3)
        self._live = self._button(playback, "Return to live radar", on_live)
        self._live.grid(row=3, column=0, sticky="ew", pady=4)
        self._label(playback, "Playback speed", small=True).grid(row=4, column=0, sticky="w")
        self._speed_buttons = self._choices(playback, 5,
            ((0.5, "0.5×"), (1.0, "1×"), (2.0, "2×")), on_speed)
        display = self._pages["display"]
        self._label(display, "Radar colors", small=True).grid(row=0, column=0, sticky="w")
        self._palette_buttons = self._choices(display, 1,
            ((False, "Universal"), (True, "Classic")), on_palette)
        self._label(display, "Radar source", small=True).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._source_buttons = self._choices(display, 3,
            ((False, "Observed"), (True, "Forecast")), on_source)
        self._label(display, "Forecast is experimental · Contiguous United States only",
                    small=True).grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self._data_status = self._label(self._body, "", small=True)
        self._data_status.configure(wraplength=540, justify=tk.LEFT, height=2)
        self._data_status.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        self._compact_body = tk.Frame(self, bg=ui.control_background, padx=12, pady=6)
        self._compact_body.grid_columnconfigure(0, weight=1)
        self._compact_timeline = tk.Scale(self._compact_body, from_=0, to=1,
            orient=tk.HORIZONTAL, showvalue=False, variable=self._value,
            command=self._scrub, resolution=1, bg=ui.control_background,
            fg=ui.control_text, troughcolor=ui.background, highlightthickness=0,
            bd=0, sliderlength=48, width=24)
        self._compact_timeline.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._button(self._compact_body, "■ Stop", self._stop_compact, width=110).grid(
            row=0, column=1)
        self._paint_choices(self._speed_buttons, speed_value)
        self._paint_choices(self._palette_buttons, classic)
        self._show_tab("playback")
        self.bind("<Escape>", lambda _event: on_close())
        self.bind("<Button-1>", self._outside_press, add="+")
        self.update_idletasks()
        self.reposition()
        self.deiconify()
        self.lift()
        # A local grab forwards taps outside the popup, including the native map,
        # so dismissal works without global application bindings.
        self.grab_set()
        self.focus_set()

    def _row(self, parent, row):
        frame = tk.Frame(parent, bg=self._ui.control_background)
        frame.grid(row=row, column=0, sticky="ew", pady=3)
        return frame

    def _label(self, parent, text, *, small=False, bold=False):
        return tk.Label(parent, text=text, bg=self._ui.control_background,
            fg=self._ui.control_text, anchor="w", wraplength=540, justify=tk.LEFT,
            font=("Sans", 11 if small else 14, "bold" if bold else "normal"))

    def _button(self, parent, text, command, *, width=None):
        return _TouchButton(parent, text, command, self._ui, width)

    def _choices(self, parent, row, choices, callback):
        frame = self._row(parent, row)
        buttons = {}
        for column, (value, text) in enumerate(choices):
            frame.grid_columnconfigure(column, weight=1, uniform=f"radar-choices-{row}")
            button = self._button(frame, text, partial(callback, value) if callback else None)
            button.grid(row=0, column=column, sticky="ew", padx=3)
            buttons[value] = (button, text)
        return buttons

    def _paint_choices(self, buttons, selected):
        for value, (button, text) in buttons.items():
            active = value == selected
            button.configure_button(text=f"✓ {text}" if active else text, selected=active,
                fg=self._ui.control_text,
                relief=tk.SUNKEN if active else tk.FLAT)

    def _show_tab(self, key):
        self._tab = key
        self._pages[key].tkraise()
        for name, button in self._tab_buttons.items():
            button.configure_button(selected=name == key,
                                    fg=self._ui.control_text,
                                    relief=tk.SUNKEN if name == key else tk.FLAT)

    def _set_compact(self, compact):
        if compact == self._compact:
            return
        self._compact = compact
        if compact:
            self._body.pack_forget()
            self._compact_body.pack(fill=tk.BOTH, expand=True)
            if self.grab_current() is self:
                self.grab_release()
        else:
            self._compact_body.pack_forget()
            self._body.pack(fill=tk.BOTH, expand=True)
            self.grab_set()
            self.focus_set()
        self.update_idletasks()
        self.reposition()

    def _stop_compact(self):
        # Stop pauses at the current frame; the controller snapshot restores
        # full controls, rather than resetting history or hiding the radar.
        if self._playing and not self._closed:
            self._on_play()

    def reposition(self):
        """Center settings; keep the slim playback strip near the map's bottom."""
        owner = self._owner_panel if self._compact else self._owner_window
        width = min(720 if self._compact else 600,
                    max(280, owner.winfo_width() - 24), self.winfo_screenwidth())
        self._data_status.configure(wraplength=max(1, width - 24))
        self._timestamp.configure(wraplength=max(1, width - 190))
        height = min(self.winfo_reqheight(), self.winfo_screenheight())
        x = max(0, min(owner.winfo_rootx() + (owner.winfo_width() - width) // 2,
                       self.winfo_screenwidth() - width))
        desired_y = (owner.winfo_rooty() + owner.winfo_height() - height - 12
                     if self._compact else owner.winfo_rooty() + (owner.winfo_height() - height) // 2)
        y = max(0, min(desired_y, self.winfo_screenheight() - height))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _outside_press(self, event):
        if not (self.winfo_rootx() <= event.x_root < self.winfo_rootx() + self.winfo_width()
                and self.winfo_rooty() <= event.y_root < self.winfo_rooty() + self.winfo_height()):
            self._on_close()
            return "break"

    def destroy(self):
        """Release input ownership on close, navigation and parent destruction."""
        if self._closed:
            return
        self._closed = True
        if self.grab_current() is self:
            self.grab_release()
        super().destroy()

    def _step(self, direction):
        if self._times and self._frame_index is not None:
            index = max(0, min(len(self._times) - 1, self._frame_index + direction))
            if index != self._frame_index:
                self._on_seek(index)

    def _scrub(self, value):
        index = int(float(value))
        if self._times and index != self._frame_index and 0 <= index < len(self._times):
            self._on_seek(index)

    def render(self, times, index, *, enabled, playing, forecast=False, loading=False,
               data_status="", refreshed_at=None, classic=False, speed=1.0):
        """Synchronize state without emitting any requests from rendering."""
        detail = data_status
        if refreshed_at is not None:
            refreshed = datetime.fromtimestamp(refreshed_at).strftime("%I:%M %p").lstrip("0")
            detail += f" · Data checked {refreshed}"
        self._data_status.configure(text=detail)
        self._times = times
        self._frame_index = index
        self._visibility.configure_button(text="✓ Radar on" if enabled else "Radar off",
            selected=enabled,
            fg=self._ui.control_text)
        self._paint_choices(self._palette_buttons, classic)
        self._paint_choices(self._source_buttons, forecast)
        self._paint_choices(self._speed_buttons, speed)
        available = enabled and bool(times)
        for timeline in (self._timeline, self._compact_timeline):
            timeline.configure(to=max(1, len(times) - 1),
                state=tk.NORMAL if available and len(times) > 1 else tk.DISABLED)
        if index is not None:
            self._value.set(index)
        self._play.configure_button(text="Ⅱ Pause" if playing else "▶ Play",
            state=tk.NORMAL if available and len(times) > 1 else tk.DISABLED)
        self._previous.configure_button(state=tk.NORMAL if available and index is not None and index > 0 else tk.DISABLED)
        self._next.configure_button(state=tk.NORMAL if available and index is not None and index < len(times) - 1 else tk.DISABLED)
        self._live.configure_button(text="Return to now" if forecast else "Return to live radar",
            state=tk.NORMAL if enabled or forecast else tk.DISABLED)
        if not enabled:
            label = "Turn radar on to load history"
        elif not times or index is None or not 0 <= index < len(times):
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
        self._oldest.configure(text=datetime.fromtimestamp(times[0]).strftime("%I:%M %p").lstrip("0") if times else "Earlier")
        self._edge.configure(text=datetime.fromtimestamp(times[-1]).strftime("%I:%M %p").lstrip("0") if forecast and times else "Latest")
        self._playing = enabled and playing
        self._set_compact(self._playing)
