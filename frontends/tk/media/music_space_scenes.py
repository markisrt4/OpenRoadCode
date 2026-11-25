# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Detailed orbital scene and a center-filled synthwave roadway."""

import math

_PLANET_COLORS = (
    (0.72, 0.31, 0.1),
    (0.05, 0.22, 0.65),
    (0.7, 0.38, 0.2),
    (0.78, 0.64, 0.38),
    (0.1, 0.55, 0.75),
)


def orbital_system(gl, glu, quadric, spectrum, pulse, elapsed, aspect=1, geometry=None):
    distance = max(10, 4.5 / (max(0.3, aspect) * math.tan(math.radians(25))))
    gl.glTranslatef(0, 0, -distance)
    gl.glRotatef(22, 1, 0, 0)
    gl.glPointSize(2)
    gl.glColor3f(0.35, 0.45, 0.7)
    gl.glBegin(gl.GL_POINTS)
    for i in range(180):
        gl.glVertex3f(math.sin(i * 2.39996) * 7, math.cos(i * 0.73) * 5, -3 - (i % 13) * 0.2)
    gl.glEnd()
    # Visible inclined orbital tracks and a glowing stellar core.
    for orbit in range(5):
        gl.glColor3f(0.12, 0.2 + orbit * 0.03, 0.35)
        gl.glBegin(gl.GL_LINE_LOOP)
        radius = 1.15 + orbit * 0.57
        for i in range(80):
            a = i * math.tau / 80
            gl.glVertex3f(math.cos(a) * radius, math.sin(a) * radius * 0.55, math.sin(a) * 0.25)
        gl.glEnd()
    gl.glColor3f(1, 0.65 + min(0.3, pulse * 0.15), 0.12)
    glu.gluSphere(quadric, 0.4 + pulse * 0.08, 32, 20)
    for ring in range(3):
        gl.glColor3f(0.8 - ring * 0.17, 0.25, 0.05)
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(64):
            a = i * math.tau / 64
            r = 0.52 + ring * 0.13 + pulse * 0.07
            gl.glVertex3f(math.cos(a) * r, math.sin(a) * r, 0)
        gl.glEnd()
    gl.glEnable(gl.GL_LIGHTING)
    gl.glDisable(gl.GL_LIGHT1)
    gl.glEnable(gl.GL_LIGHT0)
    gl.glEnable(gl.GL_COLOR_MATERIAL)
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (0, 0, 2, 1))
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (1, 0.9, 0.8, 1))
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, (0.15, 0.15, 0.22, 1))
    for planet in range(5):
        angle = elapsed * (0.25 - planet * 0.032) + planet * 1.25
        radius = 1.15 + planet * 0.57
        energy = spectrum[planet * len(spectrum) // 5]
        size = 0.16 + planet * 0.055 + energy * 0.025
        gl.glPushMatrix()
        gl.glTranslatef(
            math.cos(angle) * radius, math.sin(angle) * radius * 0.55, math.sin(angle) * 0.25
        )
        gl.glRotatef(elapsed * (12 + planet * 4), 0, 1, 0)
        color = _PLANET_COLORS[planet]
        gl.glColor3f(*color)
        gl.glPushMatrix()
        gl.glScalef(size, size, size)
        if geometry is None:
            _planet_surface(gl, planet)
        else:
            geometry.draw(("orbital-surface", planet), lambda p=planet: _planet_surface(gl, p))
        gl.glPopMatrix()
        gl.glDisable(gl.GL_LIGHTING)
        # Surface latitude bands, atmosphere and distinctive Saturn-style rings.
        gl.glBegin(gl.GL_LINES)
        for latitude in (-0.55, -0.2, 0.2, 0.55):
            r = size * math.sqrt(1 - latitude * latitude) * 1.012
            gl.glColor3f(*(channel * 0.65 for channel in color))
            for i in range(48):
                for a in (i * math.tau / 48, (i + 1) * math.tau / 48):
                    gl.glVertex3f(math.cos(a) * r, latitude * size, math.sin(a) * r)
        gl.glEnd()
        if planet in (2, 3):
            gl.glPushMatrix()
            gl.glRotatef(65 + planet * 4, 1, 0, 0)
            gl.glColor3f(0.65, 0.75, 0.85)
            glu.gluDisk(quadric, size * 1.4, size * 2.1, 64, 3)
            gl.glPopMatrix()
        moon_angle = elapsed * (0.9 + planet * 0.15)
        gl.glPushMatrix()
        gl.glTranslatef(math.cos(moon_angle) * size * 2.6, math.sin(moon_angle) * size * 2.6, 0.08)
        gl.glColor3f(0.7, 0.75, 0.85)
        glu.gluSphere(quadric, size * 0.22, 12, 8)
        gl.glPopMatrix()
        gl.glEnable(gl.GL_LIGHTING)
        gl.glPopMatrix()
    gl.glDisable(gl.GL_LIGHTING)


def electric_freeway(gl, spectrum, pulse, elapsed):
    gl.glTranslatef(0, -1.25, -1)
    gl.glColor3f(0.08, 0.32, 0.55)
    gl.glBegin(gl.GL_LINES)
    for x in range(-5, 6):
        gl.glVertex3f(x, 0, 0)
        gl.glVertex3f(x, 0, -55)
    for row in range(32):
        z = -((row * 1.7 - elapsed * (5 + pulse * 0.5)) % 54)
        gl.glVertex3f(-5, 0, z)
        gl.glVertex3f(5, 0, z)
    gl.glEnd()
    # Animated lane dashes and central energy tiles flow beneath the camera.
    gl.glBegin(gl.GL_QUADS)
    for row in range(28):
        z = -((row * 2 - elapsed * 7) % 54) - 0.2
        energy = spectrum[row % len(spectrum)]
        for x in (-0.8, 0.8):
            gl.glColor3f(0.2, 0.6 + min(0.4, pulse * 0.2), 0.9)
            for px, pz in (
                (x - 0.04, z),
                (x + 0.04, z),
                (x + 0.04, z - 0.65),
                (x - 0.04, z - 0.65),
            ):
                gl.glVertex3f(px, 0.015, pz)
        gl.glColor3f(0.4 + energy * 0.5, 0.1 + pulse * 0.12, 0.65 + energy * 0.3)
        w = 0.18 + energy * 0.25
        for px, pz in ((-w, z), (w, z), (w, z - 0.7), (-w, z - 0.7)):
            gl.glVertex3f(px, 0.025 + energy * 0.09, pz)
    gl.glEnd()
    # Spectrum gates span the road; side towers no longer carry the entire scene.
    gl.glBegin(gl.GL_LINES)
    for gate in range(12):
        z = -((gate * 4.5 - elapsed * 5) % 54) - 2
        height = 2.3 + spectrum[gate % len(spectrum)] * 0.8 + pulse * 0.3
        gl.glColor3f(0.15 + gate * 0.04, 0.7, 0.95)
        for x in (-2.2, 2.2):
            gl.glVertex3f(x, 0, z)
            gl.glVertex3f(x, height, z)
        gl.glVertex3f(-2.2, height, z)
        gl.glVertex3f(2.2, height, z)
        # Suspended equalizer strips add detail through the center of each gate.
        for band in range(10):
            x = (band / 9 - 0.5) * 3.8
            level = spectrum[(gate + band) % len(spectrum)]
            gl.glVertex3f(x, height, z)
            gl.glVertex3f(x, height - 0.2 - level * 0.75, z)
    gl.glEnd()


def _planet_surface(gl, planet):
    """Cache lit spherical terrain and gas bands; no per-frame texture generation."""
    gl.glBegin(gl.GL_QUADS)
    for latitude in range(16):
        for longitude in range(32):
            for lat, lon in (
                (latitude, longitude),
                (latitude, longitude + 1),
                (latitude + 1, longitude + 1),
                (latitude + 1, longitude),
            ):
                phi = (lat / 16 - 0.5) * math.pi
                theta = lon * math.tau / 32
                x, y, z = (
                    math.cos(phi) * math.cos(theta),
                    math.sin(phi),
                    math.cos(phi) * math.sin(theta),
                )
                noise = (
                    math.sin(theta * 3 + math.sin(phi * 5)) * math.cos(phi * 7)
                    + math.sin(theta * 7 + phi * 9) * 0.3
                )
                shade = 0.75 + 0.2 * math.sin(phi * 25) if planet in (2, 3) else 0.8 + noise * 0.12
                color = tuple(c * shade for c in _PLANET_COLORS[planet])
                if planet == 1:
                    if abs(y) > 0.85:
                        color = (0.82, 0.88, 0.92)
                    elif noise > 0.25:
                        color = (0.08, 0.42, 0.2)
                    elif noise < -0.8:
                        color = (0.65, 0.73, 0.82)
                gl.glColor3f(*color)
                gl.glNormal3f(x, y, z)
                gl.glVertex3f(x, y, z)
    gl.glEnd()
