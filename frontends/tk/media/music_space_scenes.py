# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Detailed orbital scene and a center-filled synthwave roadway."""
import math


_PLANET_COLORS = ((.72, .31, .1), (.05, .22, .65), (.7, .38, .2), (.78, .64, .38), (.1, .55, .75))


def orbital_system(gl, glu, quadric, spectrum, pulse, elapsed, aspect=1, geometry=None):
    distance = max(10, 4.5/(max(.3, aspect)*math.tan(math.radians(25))))
    gl.glTranslatef(0, 0, -distance)
    gl.glRotatef(22, 1, 0, 0)
    gl.glPointSize(2)
    gl.glColor3f(.35, .45, .7)
    gl.glBegin(gl.GL_POINTS)
    for i in range(180):
        gl.glVertex3f(math.sin(i*2.39996)*7, math.cos(i*.73)*5, -3-(i%13)*.2)
    gl.glEnd()
    # Visible inclined orbital tracks and a glowing stellar core.
    for orbit in range(5):
        gl.glColor3f(.12, .2+orbit*.03, .35)
        gl.glBegin(gl.GL_LINE_LOOP)
        radius = 1.15+orbit*.57
        for i in range(80):
            a = i*math.tau/80
            gl.glVertex3f(math.cos(a)*radius, math.sin(a)*radius*.55, math.sin(a)*.25)
        gl.glEnd()
    gl.glColor3f(1, .65+min(.3, pulse*.15), .12)
    glu.gluSphere(quadric, .4+pulse*.08, 32, 20)
    for ring in range(3):
        gl.glColor3f(.8-ring*.17, .25, .05)
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(64):
            a = i*math.tau/64
            r = .52+ring*.13+pulse*.07
            gl.glVertex3f(math.cos(a)*r, math.sin(a)*r, 0)
        gl.glEnd()
    gl.glEnable(gl.GL_LIGHTING)
    gl.glDisable(gl.GL_LIGHT1)
    gl.glEnable(gl.GL_LIGHT0)
    gl.glEnable(gl.GL_COLOR_MATERIAL)
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (0, 0, 2, 1))
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (1, .9, .8, 1))
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, (.15, .15, .22, 1))
    for planet in range(5):
        angle = elapsed*(.25-planet*.032)+planet*1.25
        radius = 1.15+planet*.57
        energy = spectrum[planet*len(spectrum)//5]
        size = .16+planet*.055+energy*.025
        gl.glPushMatrix()
        gl.glTranslatef(math.cos(angle)*radius, math.sin(angle)*radius*.55, math.sin(angle)*.25)
        gl.glRotatef(elapsed*(12+planet*4), 0, 1, 0)
        color = _PLANET_COLORS[planet]
        gl.glColor3f(*color)
        gl.glPushMatrix()
        gl.glScalef(size, size, size)
        if geometry is None:
            _planet_surface(gl, planet)
        else:
            geometry.draw(('orbital-surface', planet), lambda p=planet: _planet_surface(gl, p))
        gl.glPopMatrix()
        gl.glDisable(gl.GL_LIGHTING)
        # Surface latitude bands, atmosphere and distinctive Saturn-style rings.
        gl.glBegin(gl.GL_LINES)
        for latitude in (-.55, -.2, .2, .55):
            r = size*math.sqrt(1-latitude*latitude)*1.012
            gl.glColor3f(*(channel*.65 for channel in color))
            for i in range(48):
                for a in (i*math.tau/48, (i+1)*math.tau/48):
                    gl.glVertex3f(math.cos(a)*r, latitude*size, math.sin(a)*r)
        gl.glEnd()
        if planet in (2, 3):
            gl.glPushMatrix()
            gl.glRotatef(65+planet*4, 1, 0, 0)
            gl.glColor3f(.65, .75, .85)
            glu.gluDisk(quadric, size*1.4, size*2.1, 64, 3)
            gl.glPopMatrix()
        moon_angle = elapsed*(.9+planet*.15)
        gl.glPushMatrix()
        gl.glTranslatef(math.cos(moon_angle)*size*2.6, math.sin(moon_angle)*size*2.6, .08)
        gl.glColor3f(.7, .75, .85)
        glu.gluSphere(quadric, size*.22, 12, 8)
        gl.glPopMatrix()
        gl.glEnable(gl.GL_LIGHTING)
        gl.glPopMatrix()
    gl.glDisable(gl.GL_LIGHTING)


def electric_freeway(gl, spectrum, pulse, elapsed):
    gl.glTranslatef(0, -1.25, -1)
    gl.glColor3f(.08, .32, .55)
    gl.glBegin(gl.GL_LINES)
    for x in range(-5, 6):
        gl.glVertex3f(x, 0, 0)
        gl.glVertex3f(x, 0, -55)
    for row in range(32):
        z = -((row*1.7-elapsed*(5+pulse*.5))%54)
        gl.glVertex3f(-5, 0, z)
        gl.glVertex3f(5, 0, z)
    gl.glEnd()
    # Animated lane dashes and central energy tiles flow beneath the camera.
    gl.glBegin(gl.GL_QUADS)
    for row in range(28):
        z = -((row*2-elapsed*7)%54)-.2
        energy = spectrum[row%len(spectrum)]
        for x in (-.8, .8):
            gl.glColor3f(.2, .6+min(.4, pulse*.2), .9)
            for px, pz in ((x-.04, z), (x+.04, z), (x+.04, z-.65), (x-.04, z-.65)):
                gl.glVertex3f(px, .015, pz)
        gl.glColor3f(.4+energy*.5, .1+pulse*.12, .65+energy*.3)
        w = .18+energy*.25
        for px, pz in ((-w, z), (w, z), (w, z-.7), (-w, z-.7)):
            gl.glVertex3f(px, .025+energy*.09, pz)
    gl.glEnd()
    # Spectrum gates span the road; side towers no longer carry the entire scene.
    gl.glBegin(gl.GL_LINES)
    for gate in range(12):
        z = -((gate*4.5-elapsed*5)%54)-2
        height = 2.3+spectrum[gate%len(spectrum)]*.8+pulse*.3
        gl.glColor3f(.15+gate*.04, .7, .95)
        for x in (-2.2, 2.2):
            gl.glVertex3f(x, 0, z)
            gl.glVertex3f(x, height, z)
        gl.glVertex3f(-2.2, height, z)
        gl.glVertex3f(2.2, height, z)
        # Suspended equalizer strips add detail through the center of each gate.
        for band in range(10):
            x = (band/9-.5)*3.8
            level = spectrum[(gate+band)%len(spectrum)]
            gl.glVertex3f(x, height, z)
            gl.glVertex3f(x, height-.2-level*.75, z)
    gl.glEnd()


def _planet_surface(gl, planet):
    """Cache lit spherical terrain and gas bands; no per-frame texture generation."""
    gl.glBegin(gl.GL_QUADS)
    for latitude in range(16):
        for longitude in range(32):
            for lat, lon in ((latitude, longitude), (latitude, longitude+1),
                             (latitude+1, longitude+1), (latitude+1, longitude)):
                phi = (lat/16-.5)*math.pi
                theta = lon*math.tau/32
                x, y, z = math.cos(phi)*math.cos(theta), math.sin(phi), math.cos(phi)*math.sin(theta)
                noise = math.sin(theta*3+math.sin(phi*5))*math.cos(phi*7)+math.sin(theta*7+phi*9)*.3
                shade = .75+.2*math.sin(phi*25) if planet in (2, 3) else .8+noise*.12
                color = tuple(c*shade for c in _PLANET_COLORS[planet])
                if planet == 1:
                    if abs(y) > .85:
                        color = (.82, .88, .92)
                    elif noise > .25:
                        color = (.08, .42, .2)
                    elif noise < -.8:
                        color = (.65, .73, .82)
                gl.glColor3f(*color)
                gl.glNormal3f(x, y, z)
                gl.glVertex3f(x, y, z)
    gl.glEnd()
