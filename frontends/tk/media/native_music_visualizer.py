# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Native GL presentation. Receives analysis snapshots; owns no audio transport."""
from __future__ import annotations

import math
import time
import tkinter as tk
from tkinter import ttk

from ui.music_visualizer import VisualizerFrame
from ui.ui_widget import UiWidget
from ui.music_visualizer.music_visualizer_presentation_if import MusicVisualizerPresentationIf


class NativeMusicVisualizerPanel(tk.Frame, MusicVisualizerPresentationIf):
    """One GL surface and one animation timer, shared across visualizer/drum views."""

    def __init__(self, parent, *, theme_bundle, gl_backend, simulate=False, on_back=None):
        super().__init__(parent, bg=theme_bundle.ui.background)
        self._closed = False
        self._failed = False
        self._job = None
        self._simulate = simulate
        self._frame = VisualizerFrame(0, 0, 0, 0, (0,) * 24)
        self._received = 0.0
        self._started = time.monotonic()
        self._view = 'tunnel'
        self._double = tk.BooleanVar(value=False)
        self._sensitivity = tk.DoubleVar(value=1.5)
        self._pulse = 0.0
        controls = tk.Frame(self, bg=theme_bundle.ui.background)
        controls.pack(fill=tk.X)
        for label, view in [('Frequency Tunnel', 'tunnel'), ('Drum Kit', 'drums')]:
            ttk.Button(controls, text=label, command=lambda v=view: self._select_view(v)).pack(side=tk.LEFT, padx=3)
        ttk.Checkbutton(controls, text='Double kick', variable=self._double).pack(side=tk.LEFT, padx=6)
        response_controls = tk.Frame(self, bg=theme_bundle.ui.background)
        response_controls.pack(fill=tk.X)
        ttk.Label(response_controls, text='Beat response').pack(side=tk.LEFT)
        ttk.Scale(response_controls, from_=0.5, to=3.0, variable=self._sensitivity, length=110).pack(side=tk.LEFT)
        self._message = tk.StringVar(value='Native OpenGL · Frequency Tunnel')
        ttk.Label(self, textvariable=self._message).pack(fill=tk.X)
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
                    gl.glClearColor(0.015, 0.025, 0.055, 1)
                    gl.glEnable(gl.GL_DEPTH_TEST)
                    gl.glEnable(gl.GL_NORMALIZE)
                    self.quadric = glu.gluNewQuadric()
                    if not self.quadric:
                        raise RuntimeError('GLU geometry allocation failed')
                    glu.gluQuadricNormals(self.quadric, glu.GLU_SMOOTH)

                def redraw(self):
                    panel._draw(gl, glu, self)

            self._gl, self._glu = gl, glu
            self._surface = Surface()
            self._surface.pack(fill=tk.BOTH, expand=True)
            self._job = self.after(16, self._tick)
        except Exception as exc:
            self._fail(exc)

    def _select_view(self, view):
        self._view = view
        self._message.set('Native OpenGL · ' + ('3D Drum Kit' if view == 'drums' else 'Frequency Tunnel'))

    def _fail(self, exc):
        self._failed = True
        self._message.set(f'Native OpenGL unavailable: {exc}. Use OPENROAD_MUSIC_VISUALIZER_RENDERER=webgl to select the browser renderer.')
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def set_analysis_frame(self, frame):
        self._frame = frame
        self._received = time.monotonic()
        self._pulse = max(self._pulse, frame.beat)

    def _tick(self):
        self._job = None
        if self._closed or self._failed:
            return
        self._pulse *= math.exp(-0.016 / 0.14)
        if self._simulate:
            phase = (time.monotonic() - self._started) * 2
            pulse = math.exp(-(phase % 1) * 8)
            self.set_analysis_frame(VisualizerFrame(.5, .5, .3, .2, tuple(.3 + .2 * math.sin(phase + i) for i in range(24)), beat=pulse, kick=pulse, snare=pulse if int(phase) % 2 else 0, cymbal=pulse*.4))
        if self._surface.context_created:
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
        age = time.monotonic() - self._received
        gain = self._sensitivity.get()
        pulse = min(1.5, self._pulse * gain)
        decay = math.exp(-max(0, age - .15) / .15)
        if self._view == 'drums':
            self._drums(gl, glu, surface.quadric, pulse, decay, gain)
        else:
            self._tunnel(gl, pulse, decay)

    def _tunnel(self, gl, pulse, decay):
        gl.glDisable(gl.GL_LIGHTING)
        gl.glLineWidth(2)
        elapsed = time.monotonic() - self._started
        gl.glTranslatef(0, 0, -1.5)
        gl.glRotatef(8 * math.sin(elapsed * .25), 0, 0, 1)
        spectrum = self._frame.spectrum or (0,) * 24
        for ring in range(32):
            z = -((ring * 1.5 - elapsed * 4) % 48)
            brightness = (1 - abs(z) / 55) * (.55 + .45 * pulse)
            gl.glColor3f(.12 * brightness, (.55 + .3 * math.sin(ring*.3)) * brightness, brightness)
            gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(96):
                angle = i * math.tau / 96
                band = spectrum[(i * len(spectrum) // 96) % len(spectrum)] * decay
                radius = 2.7 + pulse * .8 + band * .45
                gl.glVertex3f(radius * math.cos(angle), radius * math.sin(angle), z)
            gl.glEnd()
        gl.glBegin(gl.GL_LINES)
        gl.glColor3f(.05, .22 + pulse*.25, .4 + pulse*.3)
        for i in range(16):
            angle = i * math.tau / 16
            radius = 2.7 + pulse * .8
            gl.glVertex3f(radius*math.cos(angle), radius*math.sin(angle), 0)
            gl.glVertex3f(radius*math.cos(angle), radius*math.sin(angle), -48)
        gl.glEnd()

    def _drums(self, gl, glu, quadric, pulse, decay, gain):
        glu.gluLookAt(0, 5.8, 9.8 - pulse*.25, 0, .5, 0, 0, 1, 0)
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_LIGHT0)
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (2, 7, 6, 1))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (.9, .95, 1, 1))
        gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT, (.18, .22, .3, 1))
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SPECULAR, (.7, .7, .7, 1))
        gl.glMaterialf(gl.GL_FRONT_AND_BACK, gl.GL_SHININESS, 48)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glColor3f(.08, .16 + pulse*.1, .23 + pulse*.15)
        gl.glBegin(gl.GL_LINES)
        for i in range(-6, 7):
            gl.glVertex3f(i, -.35, -5); gl.glVertex3f(i, -.35, 5)
            gl.glVertex3f(-6, -.35, i); gl.glVertex3f(6, -.35, i)
        gl.glEnd()
        gl.glEnable(gl.GL_LIGHTING)
        f = self._frame
        def activity(value):
            return min(1, value * gain) * decay
        # Cylinders face the viewer; shallow tilts reveal shells and chrome rims.
        drums = [(-1.15, 1.35, -.6, .6, .48, (0.55,.12,.72), f.tom_high),
                 (0, 1.5, -.9, .67, .55, (.05,.65,.48), f.tom_mid),
                 (1.4, .65, -.1, .88, .9, (.08,.4,.78), f.tom_low),
                 (-1.3, .3, 1.15, .72, .32, (.75,.38,.05), f.snare)]
        kicks = [-.65,.65] if self._double.get() else [0]
        for x in kicks:
            self._drum(gl, glu, quadric, x, .2, .6, .85, .85, (.65,.08,.12), activity(f.kick), kick=True)
        for x,y,z,r,h,color,hit in drums:
            self._drum(gl, glu, quadric, x,y,z,r,h,color,activity(hit))
        for x,y,z,r in [(-2.4,2.05,-.2,.95),(2.45,2.5,-1,.98),(-2.2,1.1,1.2,.55)]:
            hit=activity(f.cymbal)
            gl.glPushMatrix(); gl.glTranslatef(x,-.3,z)
            gl.glRotatef(-90,1,0,0)
            gl.glColor3f(.65,.68,.74)
            glu.gluCylinder(quadric,.025,.025,y+.3,12,1)
            gl.glPopMatrix()
            gl.glPushMatrix(); gl.glTranslatef(x,y,z)
            gl.glRotatef(-90 + math.sin(time.monotonic()*32)*hit*12,1,0,0)
            gl.glColor3f(.78 + hit*.2,.55 + hit*.25,.12)
            glu.gluCylinder(quadric,r,.15,.12,48,4)
            glu.gluDisk(quadric,.025,r,48,4)
            gl.glPopMatrix()
        gl.glDisable(gl.GL_LIGHTING)

    @staticmethod
    def _drum(gl, glu, q, x,y,z,r,h,color,hit,kick=False):
        gl.glPushMatrix(); gl.glTranslatef(x,y,z)
        if not kick:
            gl.glRotatef(-65,1,0,0)
        gl.glScalef(1+hit*.06,1+hit*.06,1)
        gl.glColor3f(*color); glu.gluCylinder(q,r,r,h,40,1)
        gl.glTranslatef(0,0,h)
        gl.glColor3f(.18+hit*.65,.22+hit*.6,.28+hit*.55)
        glu.gluDisk(q,0,r,40,4)
        gl.glColor3f(.7,.76,.82); glu.gluDisk(q,r*.94,r*1.025,40,1)
        for i in range(8):
            a=i*math.tau/8
            gl.glPushMatrix(); gl.glTranslatef(r*math.cos(a),r*math.sin(a),-.2)
            glu.gluCylinder(q,.035,.035,.25,8,1); gl.glPopMatrix()
        if hit>.1 and not kick:
            gl.glColor3f(.85,.67,.4)
            gl.glPushMatrix(); gl.glTranslatef(-r*.7,0,.1+hit*.18)
            gl.glRotatef(60-hit*30,0,1,0)
            glu.gluCylinder(q,.025,.025,r*1.4,10,1); gl.glPopMatrix()
        gl.glPopMatrix()

    def close(self):
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
