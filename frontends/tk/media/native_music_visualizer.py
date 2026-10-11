# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Native GL surface. Controls are supplied by the surrounding ORC screen."""
from __future__ import annotations

import math
import time
import tkinter as tk

from ui.music_visualizer import VisualizerFrame
from ui.ui_widget import UiWidget
from ui.music_visualizer.music_visualizer_presentation_if import MusicVisualizerPresentationIf
from ui.music_visualizer.music_visualizer_types import MusicVisualizerOptions, MusicVisualizerView
from .music_gl_scene import MODE_LABELS, draw_scene


class NativeMusicVisualizerPanel(tk.Frame, MusicVisualizerPresentationIf):
    """One GL surface and animation timer shared by every scene; no audio access."""

    def __init__(self, parent, *, theme_bundle, gl_backend, simulate=False, on_back=None, show_controls=False):
        super().__init__(parent, bg=theme_bundle.ui.background)
        self._closed = False
        self._failed = False
        self._job = None
        self._simulate = simulate
        self._frame = VisualizerFrame(0, 0, 0, 0, (0,) * 24)
        self._render_settings = MusicVisualizerOptions()
        self._received = 0.0
        self._started = self._last_tick = time.monotonic()
        self._pulse = 0.0
        self._status = 'Native OpenGL · Frequency Tunnel'
        self._surface = None
        try:
            Frame, gl, glu = gl_backend()
            panel = self

            class Surface(Frame, UiWidget):
                def __init__(self):
                    self.quadric = None
                    super().__init__(panel, width=1, height=1)
                    self.animate = 0

                def tkMap(self, event):
                    try:
                        self.update_idletasks()
                        super().tkMap(event)
                        if not self.context_created:
                            raise RuntimeError('No compatible GLX context')
                    except Exception as exc:
                        panel._fail(exc)

                def tkResize(self, event):
                    self.width, self.height = event.width, event.height

                def initgl(self):
                    gl.glClearColor(.015, .025, .055, 1)
                    gl.glEnable(gl.GL_DEPTH_TEST)
                    gl.glEnable(gl.GL_NORMALIZE)
                    self.quadric = glu.gluNewQuadric()
                    if not self.quadric:
                        raise RuntimeError('GLU geometry allocation failed')
                    glu.gluQuadricNormals(self.quadric, glu.GLU_SMOOTH)

                def redraw(self):
                    if not panel._closed and not panel._failed:
                        panel._draw(gl, glu, self)

            self._gl, self._glu = gl, glu
            self._surface = Surface()
            self._surface.pack(fill=tk.BOTH, expand=True)
            self._job = self.after(16, self._tick)
        except Exception as exc:
            self._fail(exc)

    def configure_visualizer(self, options: MusicVisualizerOptions) -> None:
        self._render_settings = options
        if not self._failed:
            label = '3D Drum Kit' if options.view is MusicVisualizerView.DRUM_KIT else MODE_LABELS[options.mode]
            self._status = f'Native OpenGL · {label}'

    def presentation_status(self) -> str:
        return self._status

    def _fail(self, exc):
        self._failed = True
        self._status = f'OpenGL unavailable: {exc}'
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def set_analysis_frame(self, frame: VisualizerFrame) -> None:
        if self._closed:
            return
        self._frame = frame
        self._received = time.monotonic()
        self._pulse = max(self._pulse, frame.beat)

    def _tick(self):
        self._job = None
        if self._closed or self._failed:
            return
        now = time.monotonic()
        self._pulse *= math.exp(-(now - self._last_tick) / .14)
        self._last_tick = now
        if self._simulate:
            phase = (now - self._started) * 2
            pulse = math.exp(-(phase % 1) * 8)
            self.set_analysis_frame(VisualizerFrame(
                .5, .5, .3, .2, tuple(.3 + .2 * math.sin(phase + i) for i in range(24)),
                beat=pulse, kick=pulse, snare=pulse if int(phase) % 2 else 0,
                tom_high=pulse*.2, tom_mid=pulse*.3, tom_low=pulse*.4, cymbal=pulse*.4,
            ))
        if self._surface is not None and self._surface.context_created:
            try:
                self._surface._display()
            except Exception as exc:
                self._fail(exc)
                return
        self._job = self.after(16, self._tick)

    def _draw(self, gl, glu, surface):
        width, height = max(1, surface.winfo_width()), max(1, surface.winfo_height())
        gl.glViewport(0, 0, width, height)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(50, width / height, .1, 90)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        now = time.monotonic()
        decay = math.exp(-max(0, now - self._received - .15) / .15)
        draw_scene(gl, glu, surface.quadric, self._render_settings, self._frame,
                   min(1.5, self._pulse * self._render_settings.beat_gain), decay,
                   now - self._started, width / height)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        if self._surface is not None and self._surface.context_created and self._surface.quadric:
            self._surface.tkMakeCurrent()
            self._glu.gluDeleteQuadric(self._surface.quadric)
            self._surface.quadric = None

    def destroy(self):
        self.close()
        super().destroy()
