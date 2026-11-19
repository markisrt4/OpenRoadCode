# SPDX-License-Identifier: MIT
"""Optional, actual OpenGL spectrum/waterfall surface for Tk/X11.

Requires pyopengltk and PyOpenGL, with a working compatibility GL context.
No receiver or transport logic belongs here.
"""
from __future__ import annotations

from collections.abc import Sequence
from contextlib import redirect_stdout
import io
import logging

_LOG = logging.getLogger(__name__)
_GLX_PROGRESS = ("GLX version:", "Screen is ", "Number of FBconfigs",
                 "Got a matching visual:", "Is Direct?:", "Done making a first context")


def _create_glx_context(create):
    output = io.StringIO()
    try:
        with redirect_stdout(output):
            return create()
    finally:
        for line in output.getvalue().splitlines():
            if line.startswith(_GLX_PROGRESS):
                _LOG.debug("Radio GLX: %s", line)
            elif line.strip():
                _LOG.warning("Radio GLX: %s", line)


try:
    from pyopengltk import OpenGLFrame
    from OpenGL import GL
except (ImportError, OSError):
    OpenGLFrame = None
    GL = None


def available() -> bool:
    return OpenGLFrame is not None and GL is not None


if OpenGLFrame is not None:
    class OpenGLRadioSurface(OpenGLFrame):
        """Draw the RF spectrum and historical waterfall using GPU primitives."""

        def __init__(self, parent, **kwargs):
            super().__init__(parent, **kwargs)
            self._bins: tuple[float, ...] = ()
            self._peaks: tuple[float, ...] = ()
            self._history: tuple[tuple[float, ...], ...] = ()
            self._palette = "classic"
            self._ready = False
            self._waterfall_texture = None
            self._texture_size: tuple[int, int] | None = None
            self._palette_lut: dict[str, tuple[bytes, ...]] = {}

        def tkCreateContext(self):
            return _create_glx_context(super().tkCreateContext)

        def initgl(self):
            self._ready = True
            GL.glDisable(GL.GL_DEPTH_TEST)
            self._waterfall_texture = GL.glGenTextures(1)
            self._texture_size = None
            GL.glClearColor(0.012, 0.035, 0.075, 1.0)

        def update_data(self, bins: Sequence[float],
                        history: Sequence[Sequence[float]], palette: str,
                        peaks: Sequence[float] = ()) -> None:
            self._bins = tuple(bins)
            self._peaks = tuple(peaks)
            self._history = tuple(tuple(row) for row in history)
            self._palette = palette
            if self._ready and self.winfo_exists():
                self.tkMakeCurrent()
                self.redraw()

        @staticmethod
        def _color(value: float, palette: str) -> tuple[float, float, float]:
            v = max(0.0, min(1.0, value))
            if palette == "grayscale":
                return (v, v, v)
            if v < .33:
                return (0.0, 0.0, .19 + .66 * v / .33)
            if v < .66:
                t = (v - .33) / .33
                return (.12 * t, .75 * t, 1.0)
            t = (v - .66) / .34
            return (1.0, .75 + .25 * t, .16 * (1.0 - t))

        def redraw(self):
            if not self._ready:
                return
            w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
            GL.glViewport(0, 0, w, h)
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GL.glOrtho(0, 1, 0, 1, -1, 1)
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            # Upper 38% spectrum, lower 62% waterfall.
            split = .62
            history = self._history
            if history and self._waterfall_texture is not None:
                # A single GPU texture replaces thousands of per-cell quads.
                # The texture is linearly filtered by OpenGL; converting
                # hundreds of thousands of Python RGB components per frame
                # wastes CPU without improving the displayed resolution.
                rows = min(len(history), 128)
                columns = min(max(128, w), 512)
                lut = self._palette_lut.get(self._palette)
                if lut is None:
                    lut = tuple(bytes(int(component * 255)
                                      for component in self._color(i / 255.0, self._palette))
                                for i in range(256))
                    self._palette_lut[self._palette] = lut
                pixels = bytearray(rows * columns * 3)
                for row_idx in range(rows):
                    row = history[-1 - row_idx]
                    if not row:
                        continue
                    row_len = len(row)
                    offset = row_idx * columns * 3
                    for col in range(columns):
                        value = row[col * row_len // columns]
                        index = max(0, min(255, int(value * 255)))
                        pos = offset + col * 3
                        pixels[pos:pos + 3] = lut[index]
                GL.glEnable(GL.GL_TEXTURE_2D)
                GL.glBindTexture(GL.GL_TEXTURE_2D, self._waterfall_texture)
                GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
                # Allocate storage only when dimensions change. Subsequent
                # frames update the existing GPU texture without reallocating.
                if self._texture_size != (columns, rows):
                    GL.glTexImage2D(
                        GL.GL_TEXTURE_2D, 0, GL.GL_RGB, columns, rows, 0,
                        GL.GL_RGB, GL.GL_UNSIGNED_BYTE, bytes(pixels),
                    )
                    self._texture_size = (columns, rows)
                else:
                    GL.glTexSubImage2D(
                        GL.GL_TEXTURE_2D, 0, 0, 0, columns, rows,
                        GL.GL_RGB, GL.GL_UNSIGNED_BYTE, bytes(pixels),
                    )
                GL.glColor3f(1.0, 1.0, 1.0)
                GL.glBegin(GL.GL_QUADS)
                for x, y, u, v in (
                    (0.0, 0.0, 0.0, 1.0),
                    (1.0, 0.0, 1.0, 1.0),
                    (1.0, split, 1.0, 0.0),
                    (0.0, split, 0.0, 0.0),
                ):
                    GL.glTexCoord2f(u, v)
                    GL.glVertex2f(x, y)
                GL.glEnd()
                GL.glDisable(GL.GL_TEXTURE_2D)
            if self._bins:
                GL.glColor3f(.04, .77, 1.0)
                GL.glLineWidth(2)
                GL.glBegin(GL.GL_LINE_STRIP)
                for i, value in enumerate(self._bins):
                    GL.glVertex2f(i / max(1, len(self._bins)-1),
                                  split + .38 * max(0., min(1., value)))
                GL.glEnd()
            if self._peaks:
                GL.glColor3f(.4, .95, .5)
                GL.glLineWidth(1)
                GL.glBegin(GL.GL_LINE_STRIP)
                for i, value in enumerate(self._peaks):
                    GL.glVertex2f(i / max(1, len(self._peaks)-1),
                                  split + .38 * max(0., min(1., value)))
                GL.glEnd()
            # Frequency grid aligns with the five labels above the plot.
            # Draw after the waterfall so the guides remain visible through
            # both the spectrum and the historical signal display.
            GL.glLineWidth(1)
            GL.glEnable(GL.GL_LINE_STIPPLE)
            GL.glLineStipple(1, 0x1111)
            GL.glColor3f(.30, .42, .53)
            GL.glBegin(GL.GL_LINES)
            for i in range(5):
                x = i / 4.0
                GL.glVertex2f(x, 0.0)
                GL.glVertex2f(x, 1.0)
            GL.glEnd()
            GL.glDisable(GL.GL_LINE_STIPPLE)
            GL.glColor3f(.4, .95, .5)
            GL.glBegin(GL.GL_LINES)
            GL.glVertex2f(.5, 0.)
            GL.glVertex2f(.5, 1.)
            GL.glEnd()
            # pyopengltk uses a double-buffered GLX drawable. glFlush only
            # submits commands; it does not present the back buffer.
            self.tkSwapBuffers()
else:
    class OpenGLRadioSurface:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Install pyopengltk and PyOpenGL to use OpenGL radio rendering")
