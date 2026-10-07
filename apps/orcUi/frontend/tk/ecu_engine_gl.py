# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Optional native OpenGL cutaway for the Tk ECU screen.

Imports stay inside the factory so machines without GL can use the schematic.
The inline-four is illustrative, not a model of the connected vehicle.
"""

from __future__ import annotations

import logging
import io
from contextlib import redirect_stdout
import math
import time
import os
import tkinter as tk

_LOG = logging.getLogger(__name__)


def piston_position(phase: float, cylinder: int) -> tuple[float, float, float]:
    """Slider-crank geometry: piston height and its crank pin (y, z)."""
    angle = phase * math.tau + (0 if cylinder in (0, 3) else math.pi)
    pin_y, pin_z = 0.22 * math.cos(angle), 0.22 * math.sin(angle)
    return pin_y + math.sqrt(0.78**2 - pin_z**2), pin_y, pin_z


def point_on_path(points, fraction):
    """Interpolate by distance so flow keeps a steady speed through elbows."""
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    remaining = max(0.0, min(1.0, fraction)) * sum(lengths)
    for start, end, length in zip(points, points[1:], lengths):
        if length > 0 and remaining <= length:
            return tuple(a + (b-a)*remaining/length for a, b in zip(start, end))
        remaining -= length
    return points[-1]


def create_engine_gl(parent, *, theme, on_failure, on_unavailable=None):
    """Create a GL widget, or return None when the optional backend is absent."""
    if os.environ.get("OPENROAD_ECU_RENDERER", "auto").lower() == "canvas":
        if on_unavailable is not None:
            on_unavailable("OPENROAD_ECU_RENDERER=canvas")
        return None
    try:
        from .ecu_gl_backend import load_gl_backend

        OpenGLFrame, gl, glu = load_gl_backend()
    except (ImportError, OSError, RuntimeError) as exc:
        _LOG.warning("ECU OpenGL unavailable; using schematic: %s", exc)
        if on_unavailable is not None:
            on_unavailable(str(exc))
        return None

    class EngineGL(OpenGLFrame):
        def __init__(self):
            self.phase = 0.0
            self.analysis = None
            self.failed = False
            self._drawing = False
            self._render_job = None
            self._last_render = 0.0
            self._meshes = {}
            self._scenes = {}
            self._dynamic_pass = False
            self._moving = False
            self.quadric = None
            super().__init__(parent, width=1, height=1, bg=theme.ui.surface)
            # EcuPanel owns the only animation timer, including teardown.
            self.animate = 0

        def _fail(self, exc):
            if not self.failed:
                self.failed = True
                _LOG.warning("ECU OpenGL failed; using schematic: %s", exc)
                if on_unavailable is not None:
                    on_unavailable(str(exc))
                self.after_idle(on_failure)

        def tkCreateContext(self):
            # pyopengltk prints routine GLX setup directly to stdout. Keep it
            # available at DEBUG while letting exceptions/errors report normally.
            output = io.StringIO()
            try:
                with redirect_stdout(output):
                    super().tkCreateContext()
            finally:
                if output.getvalue():
                    _LOG.debug("ECU GLX setup:\n%s", output.getvalue().rstrip())

        def tkMap(self, event):
            try:
                self.update_idletasks()
                super().tkMap(event)
                if not self.context_created:
                    raise RuntimeError("No compatible OpenGL context")
            except Exception as exc:
                self._fail(exc)

        def tkResize(self, event):
            # redraw owns viewport/projection; never reinitialize on resize.
            self.width, self.height = event.width, event.height
            if self.context_created and not self.failed:
                self._display()

        def _display(self):
            """Coalesce expose, resize, telemetry and animation into one frame."""
            if (self.failed or not self.context_created or self._render_job is not None
                    or not self.winfo_ismapped()):
                return
            delay = max(1, math.ceil(50 - (time.monotonic()-self._last_render)*1000))
            self._render_job = self.after(delay, self._render)

        def _render(self):
            self._render_job = None
            if self.failed or self._drawing or not self.winfo_ismapped():
                return
            self._drawing = True
            try:
                self.tkMakeCurrent()
                self.redraw()
                self.tkSwapBuffers()
            except Exception as exc:
                self._fail(exc)
            finally:
                self._last_render = time.monotonic()
                self._drawing = False

        def update_engine(self, analysis, phase):
            old_state = None if self.analysis is None else (
                self.analysis.engine_running, self.analysis.forced_induction_active,
            )
            changed = old_state != (analysis.engine_running, analysis.forced_induction_active) or self.phase != phase
            self.analysis, self.phase = analysis, phase
            if changed:
                self._display()

        def initgl(self):
            if not gl.glGetString(gl.GL_VERSION):
                raise RuntimeError("OpenGL context could not be initialized")
            rgb = tuple(v / 65535 for v in self.winfo_rgb(theme.ui.surface))
            gl.glClearColor(*rgb, 1)
            gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glEnable(gl.GL_NORMALIZE)
            gl.glEnable(gl.GL_LIGHTING)
            gl.glEnable(gl.GL_LIGHT0)
            gl.glEnable(gl.GL_COLOR_MATERIAL)
            gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (0.9, 0.94, 1, 1))
            gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT, (0.34, 0.38, 0.44, 1))
            gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SPECULAR, (0.5, 0.5, 0.5, 1))
            gl.glMaterialf(gl.GL_FRONT_AND_BACK, gl.GL_SHININESS, 45)
            self.quadric = glu.gluNewQuadric()
            glu.gluQuadricNormals(self.quadric, glu.GLU_SMOOTH)
            # Tessellate once per GL context; frames reuse GPU display lists.
            for name in ("tube", "sphere"):
                mesh = gl.glGenLists(1)
                if not mesh:
                    raise RuntimeError("OpenGL mesh allocation failed")
                self._meshes[name] = mesh
                gl.glNewList(mesh, gl.GL_COMPILE)
                if name == "tube":
                    glu.gluCylinder(self.quadric, 1, 1, 1, 12, 1)
                    gl.glPushMatrix()
                    gl.glRotatef(180, 1, 0, 0)
                    glu.gluDisk(self.quadric, 0, 1, 12, 1)
                    gl.glPopMatrix()
                    gl.glPushMatrix()
                    gl.glTranslatef(0, 0, 1)
                    glu.gluDisk(self.quadric, 0, 1, 12, 1)
                    gl.glPopMatrix()
                else:
                    glu.gluSphere(self.quadric, 1, 10, 6)
                gl.glEndList()


        def box(self, center, size, color):
            if self._dynamic_pass:
                return
            gl.glPushMatrix()
            gl.glTranslatef(*center)
            gl.glScalef(*size)
            gl.glColor3f(*color)
            gl.glBegin(gl.GL_QUADS)
            for normal, vertices in (
                ((0, 0, 1), ((-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))),
                ((0, 0,-1), ((1,-1,-1),(-1,-1,-1),(-1,1,-1),(1,1,-1))),
                ((0, 1, 0), ((-1,1,1),(1,1,1),(1,1,-1),(-1,1,-1))),
                ((0,-1, 0), ((-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1))),
                ((1, 0, 0), ((1,-1,1),(1,-1,-1),(1,1,-1),(1,1,1))),
                ((-1,0, 0), ((-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1))),
            ):
                gl.glNormal3f(*normal)
                for vertex in vertices:
                    gl.glVertex3f(*(v * 0.5 for v in vertex))
            gl.glEnd()
            gl.glPopMatrix()

        def tube(self, start, end, radius, color):
            if self._dynamic_pass != self._moving:
                return
            delta = tuple(b-a for a, b in zip(start, end))
            length = math.sqrt(sum(v*v for v in delta))
            if length < 1e-6:
                return
            gl.glPushMatrix()
            gl.glTranslatef(*start)
            if abs(delta[0]) + abs(delta[1]) > 1e-6:
                gl.glRotatef(math.degrees(math.acos(delta[2]/length)), -delta[1], delta[0], 0)
            elif delta[2] < 0:
                gl.glRotatef(180, 1, 0, 0)
            gl.glColor3f(*color)
            gl.glScalef(radius, radius, length)
            gl.glCallList(self._meshes["tube"])
            gl.glPopMatrix()

        def pipe(self, points, radius, color, *, flow=False):
            """Join pipe segments with round elbows."""
            if not self._dynamic_pass:
                for start, end in zip(points, points[1:]):
                    self.tube(start, end, radius, color)
                for point in points[1:-1]:
                    gl.glPushMatrix()
                    gl.glTranslatef(*point)
                    gl.glColor3f(*color)
                    gl.glScalef(radius, radius, radius)
                    gl.glCallList(self._meshes["sphere"])
                    gl.glPopMatrix()

            if flow and self._dynamic_pass and self.analysis and self.analysis.engine_running:
                self._moving = True
                highlight = tuple(min(1.0, component*0.5+0.5) for component in color)
                gl.glDisable(gl.GL_LIGHTING)
                for pulse in range(5):
                    travel = (self.phase/2 + pulse/5) % 1
                    start = point_on_path(points, travel)
                    end = point_on_path(points, min(1, travel+0.025))
                    self.tube(start, end, radius*1.15, highlight)
                gl.glEnable(gl.GL_LIGHTING)
                self._moving = False

        def turbo_housing(self, center, color, phase):
            """Snail-shaped compressor volute with a visible impeller inlet."""
            x, y, z = center
            # Growing spiral around the inlet, ending in a tangential outlet.
            points = []
            for step in range(41):
                angle = step * math.tau / 40
                radius = 0.30 + 0.09 * step / 40
                points.append((x + radius*math.cos(angle),
                               y + radius*math.sin(angle), z))
            self.pipe(points, 0.105, color)
            self.tube((x, y, z-0.16), (x, y, z+0.06), 0.25, (0.14, 0.18, 0.22))
            self.tube((x, y, z+0.07), (x, y, z+0.10), 0.075, (0.72, 0.77, 0.82))
            self._moving = True
            for blade in range(8):
                angle = phase + blade*math.tau/8
                self.tube((x+0.075*math.cos(angle), y+0.075*math.sin(angle), z+0.09),
                          (x+0.22*math.cos(angle+0.3), y+0.22*math.sin(angle+0.3), z+0.09),
                          0.025, (0.72, 0.77, 0.82))

            self._moving = False

        def redraw(self):
            w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
            gl.glViewport(0, 0, w, h)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            gl.glMatrixMode(gl.GL_PROJECTION)
            gl.glLoadIdentity()
            aspect = w / h
            extent = max(2.65, 2.40 / aspect)
            gl.glOrtho(-extent*aspect, extent*aspect, -extent, extent, 0.1, 30)
            gl.glMatrixMode(gl.GL_MODELVIEW)
            gl.glLoadIdentity()
            glu.gluLookAt(1.8, 2.4, 7.5, 0.20, 0.90, 0, 0, 1, 0)
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (-3, 5, 6, 1))
            running = bool(self.analysis and self.analysis.engine_running)
            boosted = bool(self.analysis and self.analysis.forced_induction_active)
            key = (running, boosted)
            if key not in self._scenes:
                scene = gl.glGenLists(1)
                if not scene:
                    raise RuntimeError("OpenGL scene allocation failed")
                self._scenes[key] = scene
                self._dynamic_pass = False
                gl.glNewList(scene, gl.GL_COMPILE)
                self._draw_scene(running, boosted)
                gl.glEndList()
            gl.glCallList(self._scenes[key])
            self._dynamic_pass = True
            self._draw_scene(running, boosted)

        def _draw_scene(self, running, boosted):
            self._moving = False
            metal, dark = (0.63, 0.70, 0.77), (0.22, 0.28, 0.34)
            blue = (0.18, 0.63, 0.94) if running else dark
            red = (0.85, 0.30, 0.16) if running else dark
            gold = (0.92, 0.70, 0.20) if running else dark
            # Open front block with a back wall, sump, head and cooling ribs.
            self.box((0, 0.73, -0.32), (2.85, 1.25, 0.16), dark)
            self.box((0, -0.24, 0), (2.95, 0.30, 0.8), metal)
            self.box((0, 1.53, 0), (2.95, 0.27, 0.85), metal)
            self.box((0, 1.75, 0), (2.65, 0.15, 0.70), dark)
            for y in (1.45, 1.55, 1.65):
                self.box((0, y, 0.47), (2.95, 0.035, 0.06), metal)
            self.tube((-1.62, 0, 0), (1.62, 0, 0), 0.10, metal)
            for i, x in enumerate((-1.05, -0.35, 0.35, 1.05)):
                self._moving = True
                piston_y, pin_y, pin_z = piston_position(self.phase, i)
                self.tube((x, pin_y, pin_z), (x, piston_y, 0), 0.045, metal)
                self.tube((x-0.12, pin_y, pin_z), (x+0.12, pin_y, pin_z), 0.08, metal)
                self.tube((x, piston_y-0.13, 0), (x, piston_y+0.13, 0), 0.23, metal)
                for y in (piston_y+0.05, piston_y+0.10):
                    self.tube((x, y, 0), (x, y+0.02, 0), 0.235, dark)
                # Firing order 1-3-4-2, one flash per 720-degree cycle.
                firing = (0, 0.75, 0.25, 0.5)[i]
                if running and (self.phase / 2 - firing) % 1 < 0.10:
                    self.tube((x, 1.22, 0), (x, 1.36, 0), 0.19, (1, 0.45, 0.08))
                self._moving = False
                self.tube((x, 1.90, 0.3), (x, 1.60, 0.3), 0.035, gold)
                self.tube((x, 1.48, -0.25), (x, 2.03, -0.42), 0.07, blue)
                self.pipe(((x, 1.42, 0.25), (x, 1.18, 0.72),
                           (x+0.15, 0.98, 0.72), (1.60, 0.98, 0.72)), 0.075, red)
            self.tube((-1.3, 1.93, 0.3), (1.3, 1.93, 0.3), 0.045, gold)
            self.tube((-1.3, 2.03, -0.42), (1.3, 2.03, -0.42), 0.13, blue)
            # Distinct compressor and hot-side turbine share a horizontal shaft.
            # Place the larger turbo above the head, clear of the piston cutaway.
            turbo_x, turbo_y = 0.72, 2.68
            rotor_phase = self.phase*math.tau*(3 if boosted else 1 if running else 0)
            self.turbo_housing((turbo_x, turbo_y, 0.22), metal, rotor_phase)
            self.turbo_housing((turbo_x, turbo_y, -0.35), red, rotor_phase)
            self.tube((turbo_x, turbo_y, -0.35), (turbo_x, turbo_y, 0.22), 0.08, metal)
            # Filtered air enters the compressor through a front-facing inlet.
            # A pleated filter on the left makes the fresh-air path recognizable.
            self.pipe(((-1.48, 2.65, 0.48), (-1.08, 2.65, 0.48),
                       (-0.92, 3.30, 0.48), (0.72, 3.30, 0.48),
                       (0.72, 3.02, 0.48), (0.72, 2.68, 0.34)), 0.10, blue, flow=True)
            self.tube((-1.98, 2.65, 0.48), (-1.48, 2.65, 0.48), 0.22, dark)
            for rib in range(9):
                x = -1.96 + rib*0.057
                self.tube((x, 2.65, 0.48), (x+0.023, 2.65, 0.48),
                          0.235, (0.64, 0.68, 0.71))
            for x in (-1.98, -1.51):
                self.tube((x, 2.65, 0.48), (x+0.03, 2.65, 0.48), 0.25, dark)
            # Charge pipe runs down the intake side to a finned intercooler.
            # The return pipe joins the intake plenum through a throttle body.
            self.pipe(((1.11, 2.68, 0.22), (1.11, 2.35, 0.22),
                       (-1.73, 2.35, -0.38), (-1.88, 1.95, -0.38),
                       (-1.88, -0.58, -0.38), (-1.05, -0.58, -0.38)), 0.10, blue, flow=True)
            self.box((0, -0.58, -0.38), (2.10, 0.38, 0.28), dark)
            for fin in range(22):
                self.box((-1.0+fin*0.095, -0.58, -0.21),
                         (0.035, 0.32, 0.06), metal)
            for y in (-0.77, -0.39):
                self.box((0, y, -0.38), (2.12, 0.035, 0.30), metal)
            self.pipe(((1.05, -0.58, -0.38), (1.58, -0.58, -0.38),
                       (1.58, 1.86, -0.38), (1.30, 2.03, -0.42)), 0.10, blue, flow=True)
            self.tube((1.58, 1.64, -0.38), (1.58, 1.87, -0.38), 0.15, metal)
            self.pipe(((1.60, 0.98, 0.72), (1.78, 1.28, 0.65),
                       (1.78, 2.40, -0.35), (1.11, 2.68, -0.35)), 0.095, red, flow=True)
            # Turbine outlet/downpipe stays outside the block and crankshaft.
            self.pipe(((0.72, 2.68, -0.58), (1.98, 2.68, -0.58),
                       (1.98, 0.28, 0.15)), 0.10, red, flow=True)
            # Bulged catalyst, then a separate muffler and open tailpipe below.
            self.tube((1.98, 0.28, 0.15), (1.98, -0.26, 0.15), 0.19, metal)
            for y in (0.22, -0.20):
                self.tube((1.98, y, 0.15), (1.98, y-0.025, 0.15), 0.205, dark)
            self.pipe(((1.98, -0.26, 0.15), (1.98, -0.66, 0.15),
                       (1.65, -0.87, 0.15), (0.78, -0.87, 0.15)), 0.095, red, flow=True)
            self.tube((0.78, -0.87, 0.15), (-0.42, -0.87, 0.15), 0.22, metal)
            self.tube((0.78, -0.87, 0.15), (0.72, -0.87, 0.15), 0.23, dark)
            self.tube((-0.36, -0.87, 0.15), (-0.42, -0.87, 0.15), 0.23, dark)
            self.pipe(((-0.42, -0.87, 0.15), (-1.40, -0.87, 0.15),
                       (-1.68, -0.87, 0.55)), 0.09, metal, flow=True)
            self.tube((-1.68, -0.87, 0.55), (-1.68, -0.87, 0.58), 0.066, dark)
            # Flywheel on the end of the crank.
            self.tube((-1.65, 0, 0), (-1.52, 0, 0), 0.33, dark)
            self._moving = True
            for spoke in range(4):
                a = self.phase*math.tau + spoke*math.tau/4
                self.tube((-1.67, 0, 0), (-1.67, 0.27*math.cos(a), 0.27*math.sin(a)), 0.025, metal)

            self._moving = False

        def destroy(self):
            if self._render_job is not None:
                self.after_cancel(self._render_job)
                self._render_job = None
            if self.context_created:
                self.tkMakeCurrent()
                for mesh in (*self._meshes.values(), *self._scenes.values()):
                    gl.glDeleteLists(mesh, 1)
                self._meshes.clear()
            if self.quadric is not None:
                glu.gluDeleteQuadric(self.quadric)
                self.quadric = None
            super().destroy()

    try:
        return EngineGL()
    except (tk.TclError, OSError, RuntimeError) as exc:
        _LOG.warning("ECU OpenGL widget unavailable; using schematic: %s", exc)
        if on_unavailable is not None:
            on_unavailable(str(exc))
        return None
