# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""ORC-themed control rail and native visualizer presentation."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import tkinter as tk

from ui.music_visualizer import KickMode, MusicVisualizationMode, MusicVisualizerSource
from ui.music_visualizer.music_visualizer_types import MusicVisualizerOptions, MusicVisualizerView
from ui.music_visualizer.music_visualizer_control_if import MusicVisualizerControlIf
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode
from .music_gl_scene import MODE_LABELS
from .music_visualizer_panel import MusicVisualizerPanel


class MusicVisualizerScreen(TkScreen):
    """Keep capture requests separate from local presentation settings."""

    def __init__(self, host: TkScreenHostIf, *, on_back: Callable[[], None],
                 theme_bundle: Callable[[], ThemeBundle],
                 controller: MusicVisualizerControlIf,
                 initial_source: MusicVisualizerSource,
                 panel_factory=MusicVisualizerPanel, native_controls: bool = False) -> None:
        super().__init__(ScreenId('music-visualizer'))
        self._panel_factory = panel_factory
        self._native_controls = native_controls
        self._host = host
        self._on_back = on_back
        self._theme_bundle = theme_bundle
        self._controller = controller
        self._poll_job: object | None = None
        self._closed = False
        self._panel = None
        self._source = initial_source
        self._options = MusicVisualizerOptions(mode=(MusicVisualizationMode.FREQUENCY_TUNNEL
                                                     if native_controls else MusicVisualizationMode.SPECTRUM))
        self._status: tk.StringVar | None = None
        self._renderer_status: tk.StringVar | None = None

    def set_theme_mode(self, _mode: ThemeMode) -> None:
        self.show()

    def show(self) -> None:
        if self._closed:
            return
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title('MUSIC VISUALIZER')
        self._ui = self._theme_bundle().ui
        ui = self._ui
        self._container = tk.Frame(self._host.screen_parent, bg=ui.background)
        self._container.pack(fill=tk.BOTH, expand=True)
        self._container.grid_columnconfigure(1, weight=1)
        self._container.grid_rowconfigure(0, weight=1)
        rail = tk.Frame(self._container, bg=ui.surface, highlightbackground=ui.border, highlightthickness=1)
        rail.grid(row=0, column=0, sticky='ns', padx=(0, 6))
        canvas = tk.Canvas(rail, width=164, bg=ui.surface, highlightthickness=0)
        scrollbar = tk.Scrollbar(rail, orient=tk.VERTICAL, command=canvas.yview,
                                 bg=ui.control_background, troughcolor=ui.surface,
                                 activebackground=ui.control_active, width=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        controls = tk.Frame(canvas, bg=ui.surface, padx=6, pady=6)
        window = canvas.create_window(0, 0, window=controls, anchor='nw')
        controls.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
        self._controls = controls
        self._render_parent = tk.Frame(self._container, bg=ui.background)
        self._render_parent.grid(row=0, column=1, sticky='nsew')
        self._build_controls()
        self._create_panel()
        self._status.set('Press START to connect audio.')

    def _label(self, text):
        tk.Label(self._controls, text=text, anchor='w', bg=self._ui.surface,
                 fg=self._ui.text_muted, font=('Sans', 8, 'bold')).pack(fill=tk.X, pady=(7, 3))

    def _button(self, text, action, *, active=False):
        ui = self._ui
        button = tk.Button(self._controls, text=text, command=action, relief=tk.FLAT,
                           bg=ui.accent_primary if active else ui.control_background,
                           fg=ui.control_text, activebackground=ui.control_active,
                           activeforeground=ui.control_text, font=('Sans', 9, 'bold'),
                           padx=5, pady=5, highlightthickness=1, highlightbackground=ui.border)
        button.pack(fill=tk.X, pady=2)
        return button

    def _picker(self, variable, labels, action):
        ui = self._ui
        picker = tk.OptionMenu(self._controls, variable, *labels, command=action)
        picker.configure(bg=ui.control_background, fg=ui.control_text, relief=tk.FLAT,
                         activebackground=ui.control_active, activeforeground=ui.control_text,
                         highlightthickness=1, highlightbackground=ui.border, font=('Sans', 9),
                         anchor='w')
        picker['menu'].configure(bg=ui.surface, fg=ui.text, activebackground=ui.control_active,
                                 activeforeground=ui.control_text, font=('Sans', 10))
        picker.pack(fill=tk.X, pady=2)
        return picker

    def _scale(self, variable, low, high, action):
        ui = self._ui
        tk.Scale(self._controls, variable=variable, from_=low, to=high, resolution=.1,
                 orient=tk.HORIZONTAL, command=action, length=140,
                 bg=ui.surface, fg=ui.text, troughcolor=ui.control_background,
                 activebackground=ui.accent_primary, highlightthickness=0,
                 font=('Sans', 8), sliderlength=20, bd=0).pack(fill=tk.X)

    def _build_controls(self):
        self._label('AUDIO SOURCE')
        self._source_name = tk.StringVar(value=self._source.value)
        self._picker(self._source_name, [s.value for s in MusicVisualizerSource],
                     lambda value: self._select_source(value, start=False))
        self._button('START AUDIO', lambda: self._select_source(self._source_name.get()), active=True)
        self._button('STOP', self._stop_capture)
        self._status = tk.StringVar()
        tk.Label(self._controls, textvariable=self._status, wraplength=140, anchor='w', justify=tk.LEFT,
                 bg=self._ui.surface, fg=self._ui.text_muted, font=('Sans', 8)).pack(fill=tk.X, pady=4)
        self._label('VISUALIZER')
        self._mode_name = tk.StringVar(value=MODE_LABELS[self._options.mode])
        labels = [label for mode, label in MODE_LABELS.items()
                  if self._native_controls or mode is not MusicVisualizationMode.FREQUENCY_TUNNEL]
        self._mode_picker = self._picker(self._mode_name, labels, self._select_visualizer)
        if self._native_controls:
            self._button('VISUALIZATION', lambda: self._set_options(view=MusicVisualizerView.VISUALIZER))
            self._button('DRUM KIT', lambda: self._set_options(view=MusicVisualizerView.DRUM_KIT))
            self._label('BEAT RESPONSE')
            self._gain = tk.DoubleVar(value=self._options.beat_gain)
            self._scale(self._gain, .5, 3, lambda value: self._set_options(beat_gain=float(value)))
            self._label('DRUM KIT')
            self._kick_name = tk.StringVar(value=self._options.kick_mode.value)
            self._picker(self._kick_name, ['single', 'double'],
                         lambda value: self._set_options(kick_mode=KickMode(value)))
            self._label('DRUM ZOOM')
            self._zoom = tk.DoubleVar(value=self._options.drum_zoom)
            self._scale(self._zoom, .8, 2.8, lambda value: self._set_options(drum_zoom=float(value)))
            self._sticks = tk.BooleanVar(value=self._options.show_sticks)
            tk.Checkbutton(self._controls, text='Animated sticks', variable=self._sticks,
                           command=lambda: self._set_options(show_sticks=self._sticks.get()),
                           bg=self._ui.surface, fg=self._ui.text, selectcolor=self._ui.control_background,
                           activebackground=self._ui.surface, activeforeground=self._ui.text,
                           font=('Sans', 9), anchor='w').pack(fill=tk.X, pady=3)
        self._label('CALIBRATION')
        for text, action in [('CALIBRATE', 'start_zeroize'), ('FINISH', 'finish_zeroize'), ('CLEAR', 'clear_zeroize')]:
            self._button(text, lambda operation=action: self._calibrate(operation))
        self._renderer_status = tk.StringVar()
        tk.Label(self._controls, textvariable=self._renderer_status, wraplength=140, justify=tk.LEFT,
                 bg=self._ui.surface, fg=self._ui.text_muted, font=('Sans', 8)).pack(fill=tk.X, pady=6)
        self._button('BACK TO MEDIA', self._on_back)

    def _set_options(self, **changes):
        self._options = replace(self._options, **changes)
        if self._panel is not None:
            self._panel.configure_visualizer(self._options)

    def _select_visualizer(self, label):
        mode = next(mode for mode, text in MODE_LABELS.items() if text == label)
        self._mode_name.set(label)
        self._set_options(mode=mode, view=MusicVisualizerView.VISUALIZER)

    def _create_panel(self) -> None:
        if self._panel is not None:
            self._panel.destroy()
        self._panel = self._panel_factory(
            self._render_parent, on_back=self._on_back,
            simulate=self._source is MusicVisualizerSource.SIMULATED,
            theme_bundle=self._theme_bundle(), show_controls=False,
        )
        self._panel.configure_visualizer(self._options)
        self._panel.pack(fill=tk.BOTH, expand=True)
        if self._poll_job is None:
            self._poll_job = self._host.schedule_ui_callback(16, self._poll)

    def _select_source(self, value: str, *, start: bool = True) -> None:
        self._source = MusicVisualizerSource(value)
        self._source_name.set(value)
        self._controller.stop()
        self._create_panel()
        self._status.set('Connecting audio…' if start else 'Source selected — press START')
        if start:
            self._controller.start(self._source)

    def _stop_capture(self) -> None:
        self._controller.stop()
        if self._panel is not None:
            self._panel.close()
        self._status.set('Stopped')

    def _calibrate(self, action: str) -> None:
        self._controller.calibrate(action)

    def _poll(self) -> None:
        if self._closed or self._panel is None:
            self._poll_job = None
            return
        frame, message = self._controller.presentation()
        if frame is not None:
            self._panel.set_analysis_frame(frame)
        if message is not None and self._status is not None:
            self._status.set(message)
        if self._renderer_status is not None:
            self._renderer_status.set(self._panel.presentation_status())
        self._poll_job = self._host.schedule_ui_callback(16, self._poll)

    def hide(self) -> None:
        if self._poll_job is not None:
            self._host.cancel_ui_callback(self._poll_job)
            self._poll_job = None
        if self._panel is not None:
            self._panel.close()
            self._panel.destroy()
            self._panel = None
        if not self._closed:
            self._controller.stop()

    def close(self) -> None:
        if self._closed:
            return
        self.hide()
        self._closed = True
