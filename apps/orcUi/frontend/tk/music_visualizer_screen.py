# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Media visualizer screen with bounded, thread-safe audio presentation."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import queue
import tkinter as tk
from tkinter import ttk
from collections.abc import Callable

from apps.orcUi.music_visualizer_composition import (
    MusicVisualizerSource, create_music_visualizer_session,
    selected_music_visualizer_source,
)
from apps.orcUi.music_visualizer_session import MusicVisualizerSession
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle
from .music_visualizer_panel import MusicVisualizerPanel, VisualizerFrame


class MusicVisualizerScreen(TkScreen):
    """Own capture only while the music visualizer is displayed."""

    def __init__(self, host: TkScreenHostIf, *, on_back: Callable[[], None],
                 theme_bundle: Callable[[], ThemeBundle],
                 session_factory=create_music_visualizer_session) -> None:
        super().__init__(ScreenId("music-visualizer"))
        self._host = host
        self._on_back = on_back
        self._theme_bundle = theme_bundle
        self._session_factory = session_factory
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="orc-visualizer")
        self._session: MusicVisualizerSession | None = None
        self._frames: queue.Queue[tuple[int, VisualizerFrame]] = queue.Queue(maxsize=1)
        self._messages: queue.SimpleQueue[tuple[int, str]] = queue.SimpleQueue()
        self._generation = 0
        self._poll_job: object | None = None
        self._closed = False
        self._connected_generation: int | None = None
        self._panel: MusicVisualizerPanel | None = None
        self._source = selected_music_visualizer_source()
        self._status: tk.StringVar | None = None

    def show(self) -> None:
        if self._closed:
            return
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
        picker.bind("<<ComboboxSelected>>", lambda _event: self._select_source(self._source_name.get()))
        for text, action in (
            ("START", lambda: self._select_source(self._source_name.get())),
            ("STOP", self._stop_capture),
            ("CALIBRATE", lambda: self._calibrate("start_zeroize")),
            ("FINISH", lambda: self._calibrate("finish_zeroize")),
            ("CLEAR", lambda: self._calibrate("clear_zeroize")),
        ):
            ttk.Button(controls, text=text, command=action).pack(side=tk.LEFT, padx=2)
        self._status = tk.StringVar(value="")
        tk.Label(self._container, textvariable=self._status, bg=ui.background,
                 fg=ui.text_muted, anchor="w").pack(fill=tk.X, padx=6)
        self._select_source(self._source.value)

    def _select_source(self, value: str) -> None:
        self._source = MusicVisualizerSource(value)
        self._source_name.set(value)
        self._connected_generation = None
        self._generation += 1
        if self._poll_job is not None:
            self._host.cancel_ui_callback(self._poll_job)
        if self._panel is not None:
            self._panel.destroy()
        self._panel = MusicVisualizerPanel(
            self._container, on_back=self._on_back,
            simulate=self._source is MusicVisualizerSource.SIMULATED,
        )
        self._panel.pack(fill=tk.BOTH, expand=True)
        self._status.set("Simulation — no audio capture" if self._source is MusicVisualizerSource.SIMULATED
                         else "Connecting to audio input… Android playback requires consent in the bridge.")
        self._executor.submit(self._start_capture, self._generation, self._source)
        self._poll_job = self._host.schedule_ui_callback(33, self._poll)

    def _offer_frame(self, generation: int, frame: VisualizerFrame) -> None:
        if generation != self._generation:
            return
        try:
            self._frames.get_nowait()
        except queue.Empty:
            pass
        try:
            self._frames.put_nowait((generation, frame))
        except queue.Full:
            pass

    def _start_capture(self, generation: int, source: MusicVisualizerSource) -> None:
        self._release_capture()
        if generation != self._generation:
            return
        try:
            self._session = self._session_factory(
                lambda frame: self._offer_frame(generation, frame), source=source,
            )
            if self._session is not None:
                self._session.start()
                self._connected_generation = generation
                self._messages.put((generation, "Audio input connected"))
        except Exception as exc:
            self._release_capture()
            self._messages.put((generation, f"Audio input unavailable: {exc}"))
        finally:
            if generation != self._generation:
                self._release_capture()

    def _release_capture(self) -> None:
        session, self._session = self._session, None
        if session is not None:
            session.close()

    def _stop_capture(self) -> None:
        self._generation += 1
        self._executor.submit(self._release_capture)
        self._panel.close()
        self._status.set("Stopped")

    def _calibrate(self, action: str) -> None:
        generation = self._generation
        def run() -> None:
            if generation != self._generation:
                return
            try:
                if self._session is None:
                    raise RuntimeError("Start a real audio input before calibration")
                getattr(self._session, action)()
                messages = {"start_zeroize": "Collecting ambient noise — press FINISH when ready",
                            "finish_zeroize": "Noise calibration saved",
                            "clear_zeroize": "Noise calibration cleared"}
                self._messages.put((generation, messages[action]))
            except Exception as exc:
                self._messages.put((generation, f"Calibration unavailable: {exc}"))
        self._executor.submit(run)

    def _poll(self) -> None:
        try:
            generation, frame = self._frames.get_nowait()
            if generation == self._generation and self._panel is not None:
                self._panel.set_analysis_frame(frame)
        except queue.Empty:
            pass
        while not self._messages.empty():
            generation, message = self._messages.get_nowait()
            if generation == self._generation and self._status is not None:
                self._status.set(message)
        if (self._connected_generation == self._generation
                and self._session is not None and not self._session.is_running):
            self._status.set("Audio input stopped — check the source and press START")
        self._poll_job = self._host.schedule_ui_callback(33, self._poll)

    def hide(self) -> None:
        self._generation += 1
        if self._poll_job is not None:
            self._host.cancel_ui_callback(self._poll_job)
            self._poll_job = None
        if self._panel is not None:
            self._panel.close()
            self._panel = None
        if not self._closed:
            self._executor.submit(self._release_capture)

    def close(self) -> None:
        if self._closed:
            return
        self.hide()
        self._closed = True
        self._executor.shutdown(wait=True)
