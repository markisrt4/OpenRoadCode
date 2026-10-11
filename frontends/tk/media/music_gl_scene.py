# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Native scene drawing only; receives semantic settings and analysis snapshots."""
from __future__ import annotations

import math

from ui.music_visualizer.music_visualizer_types import (
    KickMode, MusicVisualizationMode, MusicVisualizerOptions, MusicVisualizerView,
    VisualizerFrame,
)


MODE_LABELS = {
    MusicVisualizationMode.FREQUENCY_TUNNEL: 'Frequency Tunnel',
    MusicVisualizationMode.SPECTRUM: 'Spectrum Field',
    MusicVisualizationMode.ORBITING_PLANETS: 'Orbiting Planets',
    MusicVisualizationMode.ELECTRIC_FREEWAY: 'Electric Freeway',
    MusicVisualizationMode.EXPLOSION_FIELD: 'Explosion Field',
    MusicVisualizationMode.STAR_DANCE: 'Star Dance',
    MusicVisualizationMode.ELECTRIC_RINGS: 'Electric Rings',
    MusicVisualizationMode.NEON_RIBBON: 'Neon Ribbon',
    MusicVisualizationMode.KALEIDOSCOPE: 'Kaleidoscope',
}


def draw_scene(gl, glu, quadric, options: MusicVisualizerOptions, frame: VisualizerFrame,
               pulse: float, decay: float, elapsed: float, aspect: float) -> None:
    if options.view is MusicVisualizerView.DRUM_KIT:
        _drums(gl, glu, quadric, options, frame, pulse, decay, elapsed, aspect)
        return
    gl.glDisable(gl.GL_LIGHTING)
    gl.glLineWidth(2)
    spectrum = tuple(value * decay for value in frame.spectrum) or (0,) * 24
    mode = options.mode
    if mode is MusicVisualizationMode.FREQUENCY_TUNNEL:
        _tunnel(gl, spectrum, pulse, elapsed)
    elif mode is MusicVisualizationMode.SPECTRUM:
        _spectrum(gl, spectrum, pulse, elapsed)
    elif mode is MusicVisualizationMode.ORBITING_PLANETS:
        _planets(gl, glu, quadric, spectrum, pulse, elapsed)
    elif mode is MusicVisualizationMode.ELECTRIC_FREEWAY:
        _freeway(gl, spectrum, pulse, elapsed)
    elif mode is MusicVisualizationMode.EXPLOSION_FIELD:
        _particles(gl, pulse, elapsed, explode=True)
    elif mode is MusicVisualizationMode.STAR_DANCE:
        _particles(gl, pulse, elapsed, explode=False)
    elif mode is MusicVisualizationMode.ELECTRIC_RINGS:
        _rings(gl, spectrum, pulse, elapsed)
    elif mode is MusicVisualizationMode.NEON_RIBBON:
        _ribbon(gl, spectrum, pulse, elapsed)
    else:
        _kaleidoscope(gl, spectrum, pulse, elapsed)


def _tunnel(gl, spectrum, pulse, elapsed):
    gl.glTranslatef(0, 0, -1.5)
    gl.glRotatef(8 * math.sin(elapsed * .25), 0, 0, 1)
    for ring in range(28):
        z = -((ring * 1.5 - elapsed * 4) % 42)
        brightness = (1 - abs(z) / 48) * (.55 + .45 * pulse)
        gl.glColor3f(.12 * brightness, (.55 + .3 * math.sin(ring * .3)) * brightness, brightness)
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(72):
            angle = i * math.tau / 72
            band = spectrum[(i * len(spectrum) // 72) % len(spectrum)]
            radius = 2.7 + pulse * .8 + band * .45
            gl.glVertex3f(radius * math.cos(angle), radius * math.sin(angle), z)
        gl.glEnd()
    gl.glBegin(gl.GL_LINES)
    gl.glColor3f(.05, .22 + pulse * .25, .4 + pulse * .3)
    for i in range(16):
        angle = i * math.tau / 16
        radius = 2.7 + pulse * .8
        gl.glVertex3f(radius * math.cos(angle), radius * math.sin(angle), 0)
        gl.glVertex3f(radius * math.cos(angle), radius * math.sin(angle), -42)
    gl.glEnd()


def _spectrum(gl, spectrum, pulse, elapsed):
    gl.glTranslatef(0, -1.4, -8)
    gl.glRotatef(12 * math.sin(elapsed * .2), 0, 1, 0)
    for i, value in enumerate(spectrum):
        x = (i / max(1, len(spectrum) - 1) - .5) * 6
        height = .12 + value * (2.2 + pulse)
        gl.glColor3f(.12 + .7 * i / len(spectrum), .7 - .3 * i / len(spectrum), .95)
        gl.glBegin(gl.GL_QUADS)
        for z in [0, -.3]:
            for vx, vy in [(x-.08, 0), (x+.08, 0), (x+.08, height), (x-.08, height)]:
                gl.glVertex3f(vx, vy, z)
        for vx in [x-.08, x+.08]:
            for vy, z in [(0, 0), (0, -.3), (height, -.3), (height, 0)]:
                gl.glVertex3f(vx, vy, z)
        gl.glEnd()


def _planets(gl, glu, quadric, spectrum, pulse, elapsed):
    gl.glTranslatef(0, 0, -9)
    _lighting(gl)
    gl.glColor3f(1, .55 + pulse * .2, .12)
    glu.gluSphere(quadric, .45 + pulse * .2, 32, 20)
    for i in range(5):
        angle = elapsed * (.2 + i * .08) + i * 1.8
        radius = 1.1 + i * .48
        gl.glPushMatrix()
        gl.glTranslatef(math.cos(angle) * radius, math.sin(angle) * radius * .65, math.sin(angle + i) * .5)
        gl.glColor3f(.15 + i * .15, .8 - i * .08, .95 - i * .1)
        glu.gluSphere(quadric, .16 + spectrum[i * len(spectrum) // 5] * .15 + pulse * .06, 24, 16)
        gl.glPopMatrix()
    gl.glDisable(gl.GL_LIGHTING)


def _freeway(gl, spectrum, pulse, elapsed):
    gl.glTranslatef(0, -1.4, -1)
    gl.glColor3f(.15, .55 + pulse * .2, .85)
    gl.glBegin(gl.GL_LINES)
    for x in [-2, -1, 0, 1, 2]:
        gl.glVertex3f(x, 0, 0)
        gl.glVertex3f(x, 0, -50)
    for row in range(28):
        z = -((row * 2 - elapsed * 6) % 50)
        gl.glVertex3f(-4, 0, z)
        gl.glVertex3f(4, 0, z)
        height = .3 + spectrum[row % len(spectrum)] * (2 + pulse)
        for x in [-2.6, 2.6]:
            gl.glVertex3f(x, 0, z)
            gl.glVertex3f(x, height, z)
    gl.glEnd()


def _particles(gl, pulse, elapsed, *, explode):
    gl.glTranslatef(0, 0, -7)
    gl.glPointSize(3 + pulse * 3)
    gl.glBegin(gl.GL_POINTS)
    for i in range(220):
        a = i * 2.39996 + elapsed * .12
        if explode:
            radius = .2 + ((i * .137 + elapsed * .55) % 1) * (2.5 + pulse)
        else:
            radius = .4 + (i % 41) / 15 + pulse * .4
        gl.glColor3f(.25 + .65 * (i % 7) / 7, .45 + pulse * .3, .95)
        gl.glVertex3f(math.cos(a) * radius, math.sin(a) * radius, math.sin(i * .71 + elapsed) * 1.2)
    gl.glEnd()


def _rings(gl, spectrum, pulse, elapsed):
    gl.glTranslatef(0, 0, -8)
    gl.glRotatef(25 * math.sin(elapsed * .3), 0, 1, 0)
    for ring in range(7):
        gl.glColor3f(.12 + ring * .1, .8 - ring * .08, .95)
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(96):
            angle = i * math.tau / 96
            radius = .4 + ring * .3 + pulse * .22 + spectrum[i % len(spectrum)] * .08
            gl.glVertex3f(radius * math.cos(angle), radius * math.sin(angle), math.sin(angle * 3 + elapsed) * .15)
        gl.glEnd()


def _ribbon(gl, spectrum, pulse, elapsed):
    gl.glTranslatef(0, 0, -7)
    for strand in range(6):
        gl.glColor3f(.15 + strand * .12, .65, .95 - strand * .08)
        gl.glBegin(gl.GL_LINE_STRIP)
        for i in range(180):
            x = (i / 179 - .5) * 6
            band = spectrum[i * len(spectrum) // 180]
            y = math.sin(x * 2.5 + elapsed * 2 + strand * .3) * (.25 + band + pulse * .4)
            gl.glVertex3f(x, y + strand * .16 - .4, math.cos(x + elapsed) * .4)
        gl.glEnd()


def _kaleidoscope(gl, spectrum, pulse, elapsed):
    gl.glTranslatef(0, 0, -7)
    gl.glRotatef(elapsed * 12, 0, 0, 1)
    for petal in range(8):
        angle = petal * math.tau / 8
        gl.glColor3f(.25 + .6 * (petal % 3) / 3, .85, .9 - petal * .06)
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(64):
            t = i * math.tau / 64
            radius = (.8 + .7 * math.cos(t)) * (1 + pulse * .25)
            width = math.sin(t) * (.3 + spectrum[petal % len(spectrum)] * .35)
            gl.glVertex3f(radius * math.cos(angle) - width * math.sin(angle),
                          radius * math.sin(angle) + width * math.cos(angle), 0)
        gl.glEnd()


def _lighting(gl):
    gl.glEnable(gl.GL_LIGHTING)
    gl.glEnable(gl.GL_LIGHT0)
    gl.glEnable(gl.GL_COLOR_MATERIAL)
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (2, 7, 6, 1))
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (.9, .95, 1, 1))
    gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT, (.18, .22, .3, 1))
    gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SPECULAR, (.7, .7, .7, 1))
    gl.glMaterialf(gl.GL_FRONT_AND_BACK, gl.GL_SHININESS, 48)


def drum_camera_distance(zoom: float, aspect: float) -> float:
    """Zoom tightly without clipping the kit on narrow portrait surfaces."""
    # Horizontal half extent ~3.4, aim centered on the drums rather than the floor.
    fit = 3.4 / (max(.25, aspect) * math.tan(math.radians(25)))
    return max(10.5 / max(.8, zoom), fit)


def _drums(gl, glu, q, options, frame, pulse, decay, elapsed, aspect):
    distance = drum_camera_distance(options.drum_zoom, aspect)
    glu.gluLookAt(0, 1.1 + distance * .4, distance * .9 - pulse * .08,
                  0, 1.1, .1, 0, 1, 0)
    _lighting(gl)
    gl.glDisable(gl.GL_LIGHTING)
    gl.glColor3f(.08, .16 + pulse * .1, .23 + pulse * .15)
    gl.glBegin(gl.GL_LINES)
    for i in range(-4, 5):
        gl.glVertex3f(i, -.35, -3)
        gl.glVertex3f(i, -.35, 3)
        gl.glVertex3f(-4, -.35, i)
        gl.glVertex3f(4, -.35, i)
    gl.glEnd()
    gl.glEnable(gl.GL_LIGHTING)
    def activity(value):
        return min(1, value * options.beat_gain) * decay
    drums = [(-1.15, 1.35, -.6, .6, .48, (.55, .12, .72), frame.tom_high),
             (0, 1.5, -.9, .67, .55, (.05, .65, .48), frame.tom_mid),
             (1.4, .65, -.1, .88, .9, (.08, .4, .78), frame.tom_low),
             (-1.3, .3, 1.15, .72, .32, (.75, .38, .05), frame.snare)]
    kicks = [-.65, .65] if options.kick_mode is KickMode.DOUBLE else [0]
    for x in kicks:
        _drum(gl, glu, q, x, .2, .6, .85, .85, (.65, .08, .12), activity(frame.kick), kick=True)
    for x, y, z, r, h, color, hit in drums:
        _drum(gl, glu, q, x, y, z, r, h, color, activity(hit))
    cymbals = [(-2.4, 2.05, -.2, .95), (2.45, 2.5, -1, .98), (-2.2, 1.1, 1.2, .55)]
    for x, y, z, r in cymbals:
        hit = activity(frame.cymbal)
        gl.glPushMatrix()
        gl.glTranslatef(x, -.3, z)
        gl.glRotatef(-90, 1, 0, 0)
        gl.glColor3f(.65, .68, .74)
        glu.gluCylinder(q, .025, .025, y + .3, 12, 1)
        gl.glPopMatrix()
        gl.glPushMatrix()
        gl.glTranslatef(x, y, z)
        gl.glRotatef(-90 + math.sin(elapsed * 32) * hit * 12, 1, 0, 0)
        gl.glColor3f(.78 + hit * .2, .55 + hit * .25, .12)
        glu.gluCylinder(q, r, .15, .12, 48, 4)
        glu.gluDisk(q, .025, r, 48, 4)
        gl.glPopMatrix()
    if options.show_sticks:
        # Two virtual hands choose the most active reachable instrument, rather
        # than placing a separate floating stick over every piece of the kit.
        targets = [(x, y, z, r, h, -65, activity(hit)) for x, y, z, r, h, _, hit in drums]
        targets += [(x, y, z, r, 0, -90, activity(frame.cymbal)) for x, y, z, r in cymbals]
        for side in [-1, 1]:
            reachable = [target for target in targets if side * target[0] >= -.1]
            target = max(reachable, key=lambda item: item[-1])
            x, y, z, r, h, tilt, hit = target
            gl.glPushMatrix()
            gl.glTranslatef(x, y, z)
            gl.glRotatef(tilt, 1, 0, 0)
            gl.glTranslatef(side * .08, 0, h)
            _stick(gl, glu, q, r, hit)
            gl.glPopMatrix()
    gl.glDisable(gl.GL_LIGHTING)


def _stick(gl, glu, q, radius, hit):
    # A visible resting stick pivots down on attack. No unsupported drum claims.
    gl.glColor3f(.9, .72, .46)
    gl.glPushMatrix()
    gl.glTranslatef(-radius * .6, 0, .18 + (1 - hit) * .25)
    gl.glRotatef(58 + hit * 28, 0, 1, 0)
    glu.gluCylinder(q, .035, .023, radius * 1.5, 12, 1)
    gl.glTranslatef(0, 0, radius * 1.5)
    glu.gluSphere(q, .045, 12, 8)
    gl.glPopMatrix()


def _drum(gl, glu, q, x, y, z, r, h, color, hit, *, kick=False):
    gl.glPushMatrix()
    gl.glTranslatef(x, y, z)
    if not kick:
        gl.glRotatef(-65, 1, 0, 0)
    gl.glScalef(1 + hit * .06, 1 + hit * .06, 1)
    gl.glColor3f(*color)
    glu.gluCylinder(q, r, r, h, 40, 1)
    gl.glTranslatef(0, 0, h)
    gl.glColor3f(.18 + hit * .65, .22 + hit * .6, .28 + hit * .55)
    glu.gluDisk(q, 0, r, 40, 4)
    gl.glColor3f(.7, .76, .82)
    glu.gluDisk(q, r * .94, r * 1.025, 40, 1)
    for i in range(8):
        a = i * math.tau / 8
        gl.glPushMatrix()
        gl.glTranslatef(r * math.cos(a), r * math.sin(a), -.2)
        glu.gluCylinder(q, .035, .035, .25, 8, 1)
        gl.glPopMatrix()
    gl.glPopMatrix()
