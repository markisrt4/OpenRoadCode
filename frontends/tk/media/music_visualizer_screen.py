# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Media visualizer screen with bounded, thread-safe audio presentation."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from collections.abc import Callable

from ui.music_visualizer import MusicVisualizerSource
from ui.music_visualizer.music_visualizer_control_if import MusicVisualizerControlIf
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode
from .music_visualizer_panel import MusicVisualizerPanel


class MusicVisualizerScreen(TkScreen):
    """Present injected visualizer controls while hosted by any Tk shell."""

    def __init__(self, host: TkScreenHostIf, *, on_back: Callable[[], None],
                 theme_bundle: Callable[[], ThemeBundle],
                 controller: MusicVisualizerControlIf,
                 initial_source: MusicVisualizerSource,
                 panel_factory=MusicVisualizerPanel) -> None:
        super().__init__(ScreenId("music-visualizer"))
        self._panel_factory = panel_factory
        self._host = host
        self._on_back = on_back
        self._theme_bundle = theme_bundle
        self._controller = controller
        self._poll_job: object | None = None
        self._closed = False
        self._panel: MusicVisualizerPanel | None = None
        self._source = initial_source
        self._status: tk.StringVar | None = None

    def set_theme_mode(self, _mode: ThemeMode) -> None:
        self.show()

    def show(self) -> None:
        if self._closed:
            return
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("MUSIC VISUALIZER")
        ui = self._theme_bundle().ui
        self._container = tk.Frame(self._host.screen_parent, bg=ui.background)
        self._container.pack(fill=tk.BOTH, expand=True)
        controls = tk.Frame(self._container, bg=ui.background)
        controls.pack(fill=tk.X)
        self._source_name = tk.StringVar(value=self._source.value)
        picker = ttk.Combobox(controls, textvariable=self._source_name, state="readonly",
                              values=[source.value for source in MusicVisualizerSource], width=18)
        picker.pack(side=tk.LEFT, padx=6, pady=4)
        picker.bind("<<ComboboxSelected>>", lambda _event: self._select_source(self._source_name.get(), start=False))
        calibration = tk.Frame(self._container, bg=ui.background)
        calibration.pack(fill=tk.X)
        for text, action in (
            ("START", lambda: self._select_source(self._source_name.get())),
            ("STOP", self._stop_capture),
            ("CALIBRATE", lambda: self._calibrate("start_zeroize")),
            ("FINISH", lambda: self._calibrate("finish_zeroize")),
            ("CLEAR", lambda: self._calibrate("clear_zeroize")),
        ):
            row = controls if text in {"START", "STOP"} else calibration
            ttk.Button(row, text=text, command=action).pack(side=tk.LEFT, padx=2)
        self._status = tk.StringVar(value="")
        tk.Label(self._container, textvariable=self._status, bg=ui.background,
                 fg=ui.text_muted, anchor="w").pack(fill=tk.X, padx=6)
        self._create_panel()
        self._status.set("Select START to connect audio; playback consent belongs to Android Bridge.")

    def _create_panel(self) -> None:
        if self._panel is not None:
            self._panel.destroy()
        self._panel = self._panel_factory(
            self._container, on_back=self._on_back,
            simulate=self._source is MusicVisualizerSource.SIMULATED,
            theme_bundle=self._theme_bundle(),
        )
        self._panel.pack(fill=tk.BOTH, expand=True)
        if self._poll_job is None:
            self._poll_job = self._host.schedule_ui_callback(16, self._poll)

    def _select_source(self, value: str, *, start: bool = True) -> None:
        self._source = MusicVisualizerSource(value)
        self._source_name.set(value)
        self._controller.stop()
        self._create_panel()
        self._status.set("Connecting audio…" if start else "Source selected — press START")
        if start:
            self._controller.start(self._source)

    def _stop_capture(self) -> None:
        self._controller.stop()
        if self._panel is not None:
            self._panel.close()
        self._status.set("Stopped")

    def _calibrate(self, action: str) -> None:
        self._controller.calibrate(action)

    def _poll(self) -> None:
        frame, message = self._controller.presentation()
        if frame is not None and self._panel is not None:
            self._panel.set_analysis_frame(frame)
        if message is not None and self._status is not None:
            self._status.set(message)
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
