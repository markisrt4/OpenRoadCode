# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Measured spectrum display: fixed axes, configurable geometry and envelopes."""
import math

from ui.music_visualizer.music_visualizer_types import AnalyzerPalette


def measured_levels(frame):
    """Aggregate actual FFT bin peaks on the fixed logarithmic frequency axis."""
    result = []
    for i in range(64):
        low, high = 31.25 * 512 ** (i / 64), 31.25 * 512 ** ((i + 1) / 64)
        db = max((db for hz, db in zip(frame.spectrum_hz, frame.spectrum_dbfs)
                  if low <= hz < high), default=-60)
        result.append(max(0, min(1, (db + 60) / 60)))
    return result


class AnalyzerDisplay:
    """Wall-clock display envelopes, independent of audio frame arrival rate."""

    def __init__(self):
        self.levels = [0.0] * 64
        self.peaks = [0.0] * 64
        self._last = None
        self._frame = None
        self._targets = [0.0] * 64
        self._hold_until = [0.0] * 64

    def update(self, frame, appearance, now, fresh):
        dt = 0 if self._last is None else max(0, now - self._last)
        first = self._last is None
        self._last = now
        if frame is not self._frame:
            self._frame = frame
            self._targets = measured_levels(frame)
        targets = self._targets if fresh else [0.0] * 64
        for i, target in enumerate(targets):
            previous = self.levels[i]
            seconds = appearance.response_s if target > previous else appearance.decay_s
            weight = 1 if first or seconds <= 0 else -math.expm1(-dt / seconds)
            value = previous + (target - previous) * weight
            self.levels[i] = value
            if value >= self.peaks[i]:
                self.peaks[i] = value
                self._hold_until[i] = now + .5
            elif now > self._hold_until[i]:
                self.peaks[i] = max(value, self.peaks[i] - dt * .5)


def analyzer_color(appearance, height):
    """Interpolate preset/custom RGB colors from bar base to tip."""
    t = max(0, min(1, height))
    if appearance.palette is AnalyzerPalette.RETRO:
        return min(1, t * 2), min(1, (1 - t) * 2), .04
    endpoints = {
        AnalyzerPalette.ORC: ((.02, .3, .6), (.15, .85, 1)),
        AnalyzerPalette.MONO: ((.45, .65, .72), (.9, .98, 1)),
        AnalyzerPalette.FIRE: ((.9, .2, .02), (1, .85, .15)),
    }
    low, high = endpoints.get(appearance.palette, (appearance.low_color, appearance.high_color))
    return tuple(a + (b - a) * t for a, b in zip(low, high))


def draw_analyzer(gl, frame, decay, appearance, display):
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    gl.glOrtho(0, 1, 0, 1, -1, 1)
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()
    gl.glDisable(gl.GL_DEPTH_TEST)
    levels = display.levels if display is not None else [v * decay for v in measured_levels(frame)]
    peaks = display.peaks if display is not None else levels
    for db in (-60, -40, -20, 0):
        gl.glColor3f(.12, .18, .22)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(.04, .08 + (db + 60) / 60 * .86)
        gl.glVertex2f(.96, .08 + (db + 60) / 60 * .86)
        gl.glEnd()
    if appearance.range_guides:
        gl.glColor3f(.18, .3, .38)
        gl.glBegin(gl.GL_LINES)
        for hz in (250, 4000):
            x = .04 + .92 * math.log(hz / 31.25, 512)
            gl.glVertex2f(x, .08)
            gl.glVertex2f(x, .94)
        gl.glEnd()
    # Let GL interpolate linear gradients; Retro needs one extra stop at yellow.
    # Batch every bar in one draw block to avoid Python/GL calls per segment.
    gl.glShadeModel(gl.GL_SMOOTH)
    stops = (0, .5, 1) if appearance.palette is AnalyzerPalette.RETRO else (0, 1)
    colors = [analyzer_color(appearance, stop) for stop in stops]
    width = .92 / 64 * (1 - max(0, min(.8, appearance.spacing)))
    gl.glBegin(gl.GL_QUADS)
    for i, height in enumerate(levels):
        if height <= 0:
            continue
        x = .04 + .92 * i / 64
        if appearance.segmented:
            segments = [(j / 30, j / 30 + .025) for j in range(int(height * 30))]
            spans = [(bottom, top, analyzer_color(appearance, bottom / height),
                      analyzer_color(appearance, top / height)) for bottom, top in segments]
        else:
            spans = [(height * stops[j], height * stops[j+1], colors[j], colors[j+1])
                     for j in range(len(stops)-1)]
        for bottom, top, low_color, high_color in spans:
            gl.glColor3f(*low_color)
            gl.glVertex2f(x, .08 + bottom * .86)
            gl.glVertex2f(x+width, .08 + bottom * .86)
            gl.glColor3f(*high_color)
            gl.glVertex2f(x+width, .08 + top * .86)
            gl.glVertex2f(x, .08 + top * .86)
    gl.glEnd()
    if appearance.peak_markers:
        gl.glColor3f(.88, .96, 1)
        gl.glBegin(gl.GL_LINES)
        for i, peak in enumerate(peaks):
            if peak > .005:
                x = .04 + .92 * i / 64
                gl.glVertex2f(x, .08 + peak * .86)
                gl.glVertex2f(x+width, .08 + peak * .86)
        gl.glEnd()
    gl.glEnable(gl.GL_DEPTH_TEST)
