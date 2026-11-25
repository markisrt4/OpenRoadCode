# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""ORC-themed control rail and native visualizer presentation."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import replace

from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.music_visualizer import MusicVisualizationMode, MusicVisualizerSource
from ui.music_visualizer.music_visualizer_control_if import MusicVisualizerControlIf
from ui.music_visualizer.music_visualizer_types import (
    MusicCaptureState,
    MusicVisualizerOptions,
    MusicVisualizerView,
)
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode

from .music_gl_scene import MODE_LABELS
from .music_visualizer_controls import MusicVisualizerControlsMixin
from .music_visualizer_panel import MusicVisualizerPanel
from .visualizer_fullscreen import VisualizerFullscreen


class MusicVisualizerScreen(MusicVisualizerControlsMixin, TkScreen):
    """Keep capture requests separate from local presentation settings."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        on_back: Callable[[], None],
        theme_bundle: Callable[[], ThemeBundle],
        controller: MusicVisualizerControlIf,
        initial_source: MusicVisualizerSource,
        panel_factory=MusicVisualizerPanel,
        native_controls: bool = False,
        share_session: bool = False,
    ) -> None:
        super().__init__(ScreenId("music-visualizer"))
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
        self._fullscreen = None
        self._visible = False
        self._source = initial_source
        self._options = MusicVisualizerOptions(
            mode=(
                MusicVisualizationMode.FREQUENCY_TUNNEL
                if native_controls
                else MusicVisualizationMode.SPECTRUM
            )
        )
        self._status: tk.StringVar | None = None
        self._renderer_status: tk.StringVar | None = None

    def set_theme_mode(self, _mode: ThemeMode) -> None:
        self.show()

    def show(self) -> None:
        if self._closed:
            return
        self.hide()
        self._visible = True
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("MUSIC VISUALIZER")
        self._ui = self._theme_bundle().ui
        ui = self._ui
        if self._share_session:
            self._controller.attach_view(self._view_owner)
            self._options = self._controller.visualizer_options()
            self._source = self._controller.selected_source() or self._source
        self._container = tk.Frame(self._host.screen_parent, bg=ui.background)
        self._container.pack(fill=tk.BOTH, expand=True)
        self._container.grid_propagate(False)
        self._container.grid_columnconfigure(1, weight=1)
        self._container.grid_rowconfigure(0, weight=1)
        rail = tk.Frame(
            self._container,
            width=180,
            bg=ui.surface,
            highlightbackground=ui.border,
            highlightthickness=1,
        )
        rail.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        rail.pack_propagate(False)
        self._rail = rail
        self._control_font_bases = {}
        self._button_padding_bases = {}
        self._layout_signature = None
        self._resize_job = None
        self._icon_size = 26
        self._container.bind("<Configure>", lambda _event: self._schedule_control_resize())
        self._controls = tk.Frame(rail, bg=ui.surface, padx=5, pady=2)
        self._controls.pack(fill=tk.BOTH, expand=True)
        self._render_parent = tk.Frame(self._container, bg=ui.background)
        self._render_parent.grid(row=0, column=1, sticky="nsew")
        self._build_controls()
        self._create_panel()
        state = self._controller.capture_state()
        self._status.set(
            "Audio input connected"
            if state is MusicCaptureState.RUNNING
            else "Connecting audio..."
            if state is MusicCaptureState.STARTING
            else "Press START to connect audio."
        )

    def _show_page(self, page):
        if page == "STYLE" and self._options.view is MusicVisualizerView.DRUM_KIT:
            return
        self._audio_page.pack_forget()
        self._scene_page.pack_forget()
        self._style_page.pack_forget()
        if page == "STYLE":
            self._set_options(
                mode=MusicVisualizationMode.BOOMBOX, view=MusicVisualizerView.VISUALIZER
            )
        {"AUDIO": self._audio_page, "SCENE": self._scene_page, "STYLE": self._style_page}[
            page
        ].pack(fill=tk.BOTH, expand=True)

    def _update_view_buttons(self):
        style = getattr(self, "_tab_buttons", {}).get("STYLE")
        if style is not None:
            enabled = self._options.view is not MusicVisualizerView.DRUM_KIT
            style.configure(
                state=tk.NORMAL if enabled else tk.DISABLED,
                fg=self._ui.text if enabled else self._ui.text_muted,
                bg=self._ui.control_background if enabled else self._ui.surface,
            )
        for view, button in getattr(self, "_view_buttons", {}).items():
            selected = view is self._options.view
            color = (
                self._ui.accent_warning
                if view is MusicVisualizerView.DRUM_KIT
                else self._ui.accent_primary
            )
            button.configure(bg=color if selected else self._ui.control_background)

    def _select_view(self, view):
        self._set_options(view=view)
        self._show_page("SCENE")

    def _set_options(self, **changes):
        previous_view = self._options.view
        self._options = replace(self._options, **changes)
        if self._share_session:
            self._controller.configure_visualizer(self._options)
        if previous_view is not self._options.view and hasattr(self, "_scene_page"):
            self._build_scene_page()
        self._update_view_buttons()
        self._update_mode_buttons()
        if self._panel is not None:
            self._panel.configure_visualizer(self._options)
        if self._fullscreen is not None:
            self._fullscreen.configure_visualizer(self._options)

    def _update_mode_buttons(self):
        if self._options.view is not MusicVisualizerView.VISUALIZER:
            return
        if hasattr(self, "_mode_name"):
            self._mode_name.set(MODE_LABELS[self._options.mode])
        for mode, button in getattr(self, "_mode_buttons", {}).items():
            selected = mode is self._options.mode
            button.configure(
                bg=self._ui.accent_primary if selected else self._ui.control_background,
                highlightbackground=self._ui.accent_primary if selected else self._ui.border,
            )

    def _select_visualizer(self, label):
        mode = next(mode for mode, text in MODE_LABELS.items() if text == label)
        self._mode_name.set(label)
        self._set_options(mode=mode, view=MusicVisualizerView.VISUALIZER)

    def _create_panel(self) -> None:
        if self._panel is not None:
            self._panel.destroy()
        self._panel = self._panel_factory(
            self._render_parent,
            on_back=self._on_back,
            simulate=self._source is MusicVisualizerSource.SIMULATED,
            theme_bundle=self._theme_bundle(),
            show_controls=False,
        )
        self._panel.configure_visualizer(self._options)
        self._panel.pack(fill=tk.BOTH, expand=True)
        if self._poll_job is None:
            self._poll_job = self._host.schedule_ui_callback(16, self._poll)

    def _select_source(self, value: str, *, start: bool = True) -> None:
        if self._fullscreen is not None:
            self._fullscreen.close()
        self._source = MusicVisualizerSource(value)
        self._source_name.set(value)
        self._controller.stop()
        self._create_panel()
        self._status.set("Connecting audio…" if start else "Source selected — press START")
        if start:
            self._controller.start(self._source)
        self._update_capture_buttons()

    def _stop_capture(self) -> None:
        if self._fullscreen is not None:
            self._fullscreen.close()
        self._controller.stop()
        if self._panel is not None:
            self._panel.close()
        self._status.set("Stopped")
        self._update_capture_buttons()

    def _update_capture_buttons(self):
        state = self._controller.capture_state()
        active = state in (MusicCaptureState.STARTING, MusicCaptureState.RUNNING)
        for name, button in getattr(self, "_capture_buttons", {}).items():
            enabled = active if name == "STOP" else not active
            button.configure(
                state=tk.NORMAL if enabled else tk.DISABLED,
                bg=(self._ui.accent_warning if name == "STOP" else self._ui.accent_primary)
                if enabled
                else self._ui.control_background,
            )

    def _open_fullscreen(self):
        if self._fullscreen is not None:
            self._fullscreen.lift()
            return
        self._fullscreen = VisualizerFullscreen(
            self._container,
            panel_factory=self._panel_factory,
            theme_bundle=self._theme_bundle(),
            options=self._options,
            simulate=self._source is MusicVisualizerSource.SIMULATED,
            on_close=self._fullscreen_closed,
        )
        frame = self._controller.latest_frame()
        if frame is not None:
            self._fullscreen.set_analysis_frame(frame)
        if self._panel is not None:
            self._panel.pack_forget()

    def _fullscreen_closed(self):
        self._fullscreen = None
        if self._visible and not self._closed and self._panel is not None:
            self._panel.pack(fill=tk.BOTH, expand=True)

    def _calibrate(self, action: str) -> None:
        self._controller.calibrate(action)

    def _poll(self) -> None:
        if self._closed or self._panel is None:
            self._poll_job = None
            return
        self._update_capture_buttons()
        frame, message = self._controller.presentation()
        if frame is not None:
            self._panel.set_analysis_frame(frame)
            if self._fullscreen is not None:
                self._fullscreen.set_analysis_frame(frame)
        if message is not None and self._status is not None:
            self._status.set(message)
        if self._renderer_status is not None:
            rendering = self._panel.presentation_status()
            self._renderer_status.set(rendering)
            if rendering.startswith("OpenGL unavailable") and self._status is not None:
                self._status.set(rendering)
        self._poll_job = self._host.schedule_ui_callback(16, self._poll)

    def hide(self) -> None:
        self._visible = False
        if self._fullscreen is not None:
            self._fullscreen.close()
        if getattr(self, "_resize_job", None) is not None:
            self._container.after_cancel(self._resize_job)
            self._resize_job = None
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
