# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Distinct native spark, star and mirrored-facet scenes; batched geometry."""

import colorsys
import math


def explosion_field(gl, pulse, elapsed):
    gl.glTranslatef(0, 0, -8)
    gl.glBegin(gl.GL_LINES)
    for emitter, (cx, cy) in enumerate(((-1.7, 0.8), (1.4, 0.6), (0, -1.1))):
        age = (elapsed * 0.55 + emitter / 3) % 1
        radius = 0.15 + age * (2.2 + pulse)
        for i in range(120):
            angle = i * 2.39996 + emitter
            dz = 1 - 2 * (i + 0.5) / 120
            planar = math.sqrt(1 - dz * dz)
            ux, uy = math.cos(angle) * planar, math.sin(angle) * planar
            shade = (1 - age * 0.7) * (0.65 + pulse * 0.25)
            gl.glColor3f(shade, shade * (0.25 + i % 5 * 0.1), 0.07)
            for distance in (max(0, radius - 0.12 - age * 0.2), radius):
                gl.glVertex3f(
                    cx + ux * distance, cy + uy * distance - age * age * 0.5, dz * distance
                )
    gl.glEnd()
    # Short hot shockwaves highlight musical onsets.
    if pulse > 0.04:
        for cx, cy in ((-1.7, 0.8), (1.4, 0.6), (0, -1.1)):
            gl.glColor3f(min(1, pulse), 0.35 * pulse, 0.1)
            gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(48):
                a = i * math.tau / 48
                gl.glVertex3f(cx + math.cos(a) * (1 + pulse), cy + math.sin(a) * (1 + pulse), 0)
            gl.glEnd()


def _flat_view(gl, aspect):
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    gl.glOrtho(-aspect, aspect, -1, 1, -1, 1)
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()
    gl.glDisable(gl.GL_DEPTH_TEST)


def star_dance(gl, spectrum, pulse, elapsed, aspect):
    _flat_view(gl, aspect)
    gl.glPointSize(2)
    gl.glColor3f(0.22, 0.35, 0.6)
    gl.glBegin(gl.GL_POINTS)
    for i in range(100):
        gl.glVertex2f(((i * 0.61803) % 1 * 2 - 1) * aspect, (i * 0.4142 + elapsed * 0.018) % 2 - 1)
    gl.glEnd()
    # Filled, spinning five-point stars weave through a drifting starfield.
    gl.glBegin(gl.GL_TRIANGLES)
    for i in range(32):
        cx = math.sin(i * 2.39996 + elapsed * 0.12) * aspect * 0.88
        cy = (i * 0.137 + elapsed * (0.035 + i % 3 * 0.008)) % 2.3 - 1.15
        size = 0.045 + (i % 4) * 0.013 + spectrum[i % len(spectrum)] * 0.018 + pulse * 0.025
        spin = elapsed * (0.25 + i % 3 * 0.12) + i
        gl.glColor3f(
            *colorsys.hsv_to_rgb((0.52 + i * 0.013) % 1, 0.5, 0.65 + min(0.35, pulse * 0.3))
        )
        for point in range(10):
            gl.glVertex2f(cx, cy)
            for k in (point, point + 1):
                a = spin + k * math.pi / 5
                r = size if k % 2 == 0 else size * 0.42
                gl.glVertex2f(cx + math.sin(a) * r, cy + math.cos(a) * r)
    gl.glEnd()
    gl.glEnable(gl.GL_DEPTH_TEST)


def kaleidoscope(gl, spectrum, pulse, elapsed, aspect):
    _flat_view(gl, aspect)
    gl.glRotatef(elapsed * 5, 0, 0, 1)
    extent = math.hypot(aspect, 1) * 1.05
    # Every wedge mirrors its neighbor. Six layers fill the entire viewport.
    gl.glBegin(gl.GL_TRIANGLES)
    for sector in range(16):
        base = sector * math.tau / 16
        direction = 1 if sector % 2 == 0 else -1
        origin = base if direction == 1 else base + math.tau / 16
        for layer in range(6):
            for facet in range(3):
                band = spectrum[(layer * 3 + facet) % len(spectrum)]
                inner = extent * layer / 6
                outer = extent * (layer + 1) / 6
                middle = (inner + outer) / 2 + math.sin(
                    elapsed * 0.6 + layer
                ) * extent * 0.025 * band
                angle1 = origin + direction * facet * math.tau / 48
                angle2 = origin + direction * (facet + 1) * math.tau / 48
                vertices = (
                    (inner, angle1),
                    (outer, angle1),
                    (middle, angle2),
                    (outer, angle1),
                    (outer, angle2),
                    (middle, angle2),
                    (inner, angle1),
                    (middle, angle2),
                    (inner, angle2),
                )
                for triangle in range(3):
                    hue = (elapsed * 0.025 + layer * 0.12 + facet * 0.08 + triangle * 0.025) % 1
                    color = colorsys.hsv_to_rgb(
                        hue, 0.7, min(1, 0.3 + band * 0.35 + pulse * 0.25 + triangle * 0.1)
                    )
                    gl.glColor3f(*color)
                    for radius, angle in vertices[triangle * 3 : triangle * 3 + 3]:
                        gl.glVertex2f(math.cos(angle) * radius, math.sin(angle) * radius)
    gl.glEnd()
    gl.glEnable(gl.GL_DEPTH_TEST)
