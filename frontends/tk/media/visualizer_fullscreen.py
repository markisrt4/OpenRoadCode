# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Immersive native presentation using the existing capture and scene preferences."""
import tkinter as tk

from ui.music_visualizer.music_visualizer_presentation_if import MusicVisualizerPresentationIf
from ui.music_visualizer.music_visualizer_types import MusicVisualizerOptions, VisualizerFrame


class VisualizerFullscreen(tk.Toplevel, MusicVisualizerPresentationIf):
    """Own a fullscreen surface; its screen supplies frames and cleanup."""

    def __init__(self, parent, *, panel_factory, theme_bundle, options, simulate, on_close):
        super().__init__(parent)
        self._closed = False
        self._panel = None
        self._on_close = on_close
        self.title('ORC Visualizer')
        self.configure(bg=theme_bundle.ui.background)
        self.geometry(f'{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0')
        self.attributes('-fullscreen', True)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda _event: self.close())
        self.bind('<F11>', lambda _event: self.close())
        tk.Button(self, text='EXIT FULLSCREEN  (Esc / F11)', command=self.close,
                  bg=theme_bundle.ui.control_background, fg=theme_bundle.ui.control_text,
                  activebackground=theme_bundle.ui.control_active, relief=tk.FLAT,
                  font=('Sans', 10, 'bold'), pady=5).pack(fill=tk.X)
        try:
            self._panel = panel_factory(self, theme_bundle=theme_bundle, simulate=simulate,
                                        on_back=self.close, show_controls=False)
            self._panel.configure_visualizer(options)
            self._panel.pack(fill=tk.BOTH, expand=True)
            self.focus_set()
        except Exception:
            self.close()
            raise

    def configure_visualizer(self, options: MusicVisualizerOptions) -> None:
        if not self._closed and self._panel is not None:
            self._panel.configure_visualizer(options)

    def set_analysis_frame(self, frame: VisualizerFrame) -> None:
        if not self._closed and self._panel is not None:
            self._panel.set_analysis_frame(frame)

    def presentation_status(self) -> str:
        return self._panel.presentation_status() if self._panel is not None else ''

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._panel is not None:
                self._panel.close()
        finally:
            self._on_close()
            super().destroy()

    def destroy(self) -> None:
        self.close()
