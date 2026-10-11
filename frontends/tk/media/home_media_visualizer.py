# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Selectable visualizer preview inside the existing HOME Media card."""
from __future__ import annotations

import tkinter as tk

from ui.ui_widget import UiWidget
from ui.music_visualizer.music_visualizer_control_if import MusicVisualizerControlIf
from ui.music_visualizer.music_visualizer_presentation_if import MusicVisualizerPresentationIf
from ui.music_visualizer import MusicVisualizerSource


class HomeMediaVisualizer(tk.Frame, UiWidget):
    """Own only the mounted presentation; capture and preferences remain shared."""

    def __init__(self, parent, *, controller: MusicVisualizerControlIf, theme_bundle,
                 now_playing_factory, visualizer_factory, source: MusicVisualizerSource,
                 on_open):
        self._theme = theme_bundle()
        ui = self._theme.ui
        super().__init__(parent, bg=ui.surface)
        self._controller = controller
        self._now_playing_factory = now_playing_factory
        self._visualizer_factory = visualizer_factory
        self._source = source
        self._on_open = on_open
        self._owner = f'home-visualizer-{id(self)}'
        self._closed = False
        self._poll_job = None
        self._preview: MusicVisualizerPresentationIf | None = None
        self._attached = False
        self._last_frame = None
        self._body = tk.Frame(self, bg=ui.surface)
        selector = tk.Frame(self, bg=ui.surface)
        selector.pack(fill=tk.X)
        self._buttons = {}
        for text, enabled in [('PLAYING', False), ('VISUALIZER', True)]:
            button = tk.Button(selector, text=text, command=lambda v=enabled: self._select(v),
                               bg=ui.control_background, fg=ui.control_text,
                               activebackground=ui.control_active, relief=tk.FLAT,
                               font=('Sans', 7, 'bold'), pady=3, padx=1)
            button.pack(side=tk.LEFT, expand=True, fill=tk.X)
            self._buttons[enabled] = button
        self._body.pack(fill=tk.BOTH, expand=True)
        self._footer = tk.Frame(self, bg=ui.surface)
        self._footer.pack(fill=tk.X)
        tk.Button(self._footer, text='START', command=lambda: controller.start(controller.selected_source() or source),
                  bg=ui.accent_primary, fg=ui.control_text, relief=tk.FLAT,
                  font=('Sans', 7, 'bold'), pady=2).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(self._footer, text='OPEN', command=on_open,
                  bg=ui.control_background, fg=ui.control_text, relief=tk.FLAT,
                  font=('Sans', 7, 'bold'), pady=2).pack(side=tk.LEFT, expand=True, fill=tk.X)
        self._select(controller.home_visualizer_enabled())

    def _select(self, enabled: bool):
        if self._closed:
            return
        self._retire_preview()
        for child in self._body.winfo_children():
            child.destroy()
        self._controller.set_home_visualizer_enabled(enabled)
        for value, button in self._buttons.items():
            button.configure(bg=self._theme.ui.accent_primary if value == enabled
                             else self._theme.ui.control_background)
        if enabled:
            self._footer.pack(fill=tk.X)
            self._controller.attach_view(self._owner)
            self._attached = True
            try:
                self._preview = self._visualizer_factory(self._body)
            except Exception:
                self._retire_preview()
                raise
            self._preview.configure_visualizer(self._controller.visualizer_options())
            self._preview.pack(fill=tk.BOTH, expand=True)
            self._preview.bind('<Button-1>', lambda _: self._on_open(), add='+')
            # The native surface receives the click; bind the child widgets too.
            for child in self._preview.winfo_children():
                child.bind('<Button-1>', lambda _: self._on_open(), add='+')
            self._poll()
        else:
            self._footer.pack_forget()
            self._now_playing_factory(self._body).pack(fill=tk.BOTH, expand=True)

    def _poll(self):
        self._poll_job = None
        if self._closed or self._preview is None:
            return
        frame = self._controller.latest_frame()
        if frame is not None and frame is not self._last_frame:
            self._preview.set_analysis_frame(frame)
            self._last_frame = frame
        self._preview.configure_visualizer(self._controller.visualizer_options())
        self._poll_job = self.after(33, self._poll)

    def _retire_preview(self):
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        if self._preview is not None:
            self._preview.close()
            self._preview.destroy()
            self._preview = None
        if self._attached:
            self._controller.detach_view(self._owner)
            self._attached = False
        self._last_frame = None

    def close(self):
        if not self._closed:
            self._closed = True
            self._retire_preview()

    def destroy(self):
        self.close()
        super().destroy()
