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
                 panel_factory=MusicVisualizerPanel, native_controls: bool = False,
                 share_session: bool = False) -> None:
        super().__init__(ScreenId('music-visualizer'))
        self._panel_factory = panel_factory
        self._native_controls = native_controls
        self._share_session = share_session
        self._view_owner = f"full-visualizer-{id(self)}"
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
        if self._share_session:
            self._controller.attach_view(self._view_owner)
            self._options = self._controller.visualizer_options()
            self._source = self._controller.selected_source() or self._source
        self._container = tk.Frame(self._host.screen_parent, bg=ui.background)
        self._container.pack(fill=tk.BOTH, expand=True)
        self._container.grid_columnconfigure(1, weight=1)
        self._container.grid_rowconfigure(0, weight=1)
        rail = tk.Frame(self._container, width=180, bg=ui.surface,
                        highlightbackground=ui.border, highlightthickness=1)
        rail.grid(row=0, column=0, sticky='ns', padx=(0, 6))
        rail.pack_propagate(False)
        self._controls = tk.Frame(rail, bg=ui.surface, padx=5, pady=2)
        self._controls.pack(fill=tk.BOTH, expand=True)
        self._render_parent = tk.Frame(self._container, bg=ui.background)
        self._render_parent.grid(row=0, column=1, sticky='nsew')
        self._build_controls()
        self._create_panel()
        self._status.set('Press START to connect audio.')

    def _label(self, text):
        tk.Label(self._controls, text=text, anchor='w', bg=self._ui.surface,
                 fg=self._ui.text_muted, font=('Sans', 8, 'bold')).pack(fill=tk.X, pady=(3, 1))

    def _button(self, text, action, *, active=False):
        ui = self._ui
        button = tk.Button(self._controls, text=text, command=action, relief=tk.FLAT,
                           bg=ui.accent_primary if active else ui.control_background,
                           fg=ui.control_text, activebackground=ui.control_active,
                           activeforeground=ui.control_text, font=('Sans', 9, 'bold'),
                           padx=3, pady=3, highlightthickness=1, highlightbackground=ui.border)
        button.pack(fill=tk.X, pady=1)
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
        picker.pack(fill=tk.X, pady=1)
        return picker

    def _scale(self, variable, low, high, action):
        ui = self._ui
        row = tk.Frame(self._controls, bg=ui.surface)
        row.pack(fill=tk.X)
        tk.Label(row, textvariable=variable, width=4, bg=ui.surface, fg=ui.text,
                 font=('Sans', 8)).pack(side=tk.RIGHT)
        tk.Scale(row, variable=variable, from_=low, to=high, resolution=.1,
                 orient=tk.HORIZONTAL, command=action, length=110, showvalue=False,
                 bg=ui.surface, fg=ui.text, troughcolor=ui.control_background,
                 activebackground=ui.accent_primary, highlightthickness=0,
                 font=('Sans', 8), sliderlength=20, bd=0).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_controls(self):
        self._rail_body = self._controls
        self._view_buttons = {}
        if self._native_controls:
            views = tk.Frame(self._controls, bg=self._ui.surface)
            views.pack(fill=tk.X, pady=(0, 3))
            for label, view in [('VISUALS', MusicVisualizerView.VISUALIZER),
                                ('DRUMS', MusicVisualizerView.DRUM_KIT)]:
                button = tk.Button(views, text=label,
                                   command=lambda v=view: self._select_view(v),
                                   relief=tk.FLAT, font=('Sans', 9, 'bold'), pady=4,
                                   fg=self._ui.control_text,
                                   activebackground=self._ui.control_active)
                button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
                self._view_buttons[view] = button
        tabs = tk.Frame(self._controls, bg=self._ui.surface)
        tabs.pack(fill=tk.X)
        for name in ['AUDIO', 'SCENE']:
            tk.Button(tabs, text=name, command=lambda n=name: self._show_page(n),
                      relief=tk.FLAT, bg=self._ui.control_background, fg=self._ui.text_muted,
                      activebackground=self._ui.control_active, font=('Sans', 8, 'bold'),
                      pady=3).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        self._page_host = tk.Frame(self._controls, bg=self._ui.surface)
        self._page_host.pack(fill=tk.BOTH, expand=True, pady=3)
        self._audio_page = tk.Frame(self._page_host, bg=self._ui.surface)
        self._scene_page = tk.Frame(self._page_host, bg=self._ui.surface)
        self._controls = self._audio_page
        self._label('SOURCE')
        self._source_name = tk.StringVar(value=self._source.value)
        self._picker(self._source_name, [s.value for s in MusicVisualizerSource],
                     lambda value: self._select_source(value, start=False))
        self._label('NOISE CALIBRATION')
        calibration = tk.Frame(self._controls, bg=self._ui.surface)
        calibration.pack(fill=tk.X, pady=2)
        for text, operation in [('CAL', 'start_zeroize'), ('SAVE', 'finish_zeroize'), ('CLEAR', 'clear_zeroize')]:
            tk.Button(calibration, text=text, command=lambda op=operation: self._calibrate(op),
                      relief=tk.FLAT, bg=self._ui.control_background, fg=self._ui.control_text,
                      activebackground=self._ui.control_active, font=('Sans', 8, 'bold'),
                      pady=4).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        tk.Label(self._controls, text='Pause music: CAL → SAVE', bg=self._ui.surface,
                 fg=self._ui.text_muted, font=('Sans', 7)).pack(fill=tk.X)
        self._build_scene_page()
        self._controls = self._rail_body
        footer = tk.Frame(self._controls, bg=self._ui.surface)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        start_stop = tk.Frame(footer, bg=self._ui.surface)
        start_stop.pack(fill=tk.X)
        for text, action, color in [('START', lambda: self._select_source(self._source_name.get()), self._ui.accent_primary),
                                   ('STOP', self._stop_capture, self._ui.control_background)]:
            tk.Button(start_stop, text=text, command=action, bg=color, fg=self._ui.control_text,
                      activebackground=self._ui.control_active, relief=tk.FLAT,
                      font=('Sans', 9, 'bold'), pady=4).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        self._status = tk.StringVar()
        self._renderer_status = tk.StringVar()
        tk.Label(footer, textvariable=self._status, height=2, wraplength=165,
                 anchor='w', justify=tk.LEFT, bg=self._ui.surface, fg=self._ui.text_muted,
                 font=('Sans', 8)).pack(fill=tk.X, pady=1)
        self._show_page('SCENE')
        self._update_view_buttons()

    def _build_scene_page(self):
        for child in self._scene_page.winfo_children():
            child.destroy()
        previous = self._controls
        self._controls = self._scene_page
        self._mode_name = tk.StringVar(value=MODE_LABELS[self._options.mode])
        if self._options.view is MusicVisualizerView.DRUM_KIT:
            self._kick_name = tk.StringVar(value=self._options.kick_mode.value)
            self._picker(self._kick_name, ['single', 'double'],
                         lambda value: self._set_options(kick_mode=KickMode(value)))
            self._label('DRUM RESPONSE')
            self._drum_gain = tk.DoubleVar(value=self._options.drum_gain)
            self._scale(self._drum_gain, .2, 1.2,
                        lambda value: self._set_options(drum_gain=float(value)))
            self._label('DRUM ZOOM')
            self._zoom = tk.DoubleVar(value=self._options.drum_zoom)
            self._scale(self._zoom, .8, 2.8, lambda value: self._set_options(drum_zoom=float(value)))
        else:
            labels = [label for mode, label in MODE_LABELS.items()
                      if self._native_controls or mode is not MusicVisualizationMode.FREQUENCY_TUNNEL]
            self._mode_picker = self._picker(self._mode_name, labels, self._select_visualizer)
            if self._native_controls:
                self._label('BEAT RESPONSE')
                self._gain = tk.DoubleVar(value=self._options.beat_gain)
                self._scale(self._gain, .5, 3, lambda value: self._set_options(beat_gain=float(value)))
        self._controls = previous

    def _show_page(self, page):
        self._audio_page.pack_forget()
        self._scene_page.pack_forget()
        (self._audio_page if page == 'AUDIO' else self._scene_page).pack(fill=tk.BOTH, expand=True)

    def _update_view_buttons(self):
        for view, button in getattr(self, '_view_buttons', {}).items():
            selected = view is self._options.view
            color = (self._ui.accent_warning if view is MusicVisualizerView.DRUM_KIT
                     else self._ui.accent_primary)
            button.configure(bg=color if selected else self._ui.control_background)

    def _select_view(self, view):
        self._set_options(view=view)
        self._show_page('SCENE')

    def _set_options(self, **changes):
        previous_view = self._options.view
        self._options = replace(self._options, **changes)
        if self._share_session:
            self._controller.configure_visualizer(self._options)
        if previous_view is not self._options.view and hasattr(self, '_scene_page'):
            self._build_scene_page()
        self._update_view_buttons()
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
            rendering = self._panel.presentation_status()
            self._renderer_status.set(rendering)
            if rendering.startswith('OpenGL unavailable') and self._status is not None:
                self._status.set(rendering)
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
            if self._share_session:
                self._controller.detach_view(self._view_owner)
            else:
                self._controller.stop()

    def close(self) -> None:
        if self._closed:
            return
        self.hide()
        self._closed = True
