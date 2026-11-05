# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Isolated X11 event sender: no pointer warp, global key press or focus change.

Run in a child process so an X11 BadWindow cannot terminate Tk. Scrcpy receives
its normal drag / Ctrl-drag events and forwards them to its own virtual display.
"""
import ctypes as c
from ctypes.util import find_library
import json
import signal
import sys
import time

from ui.navigation.waze_gesture_if import WazeGesture


class KeyButtonEvent(c.Structure):
    _fields_ = [('type', c.c_int), ('serial', c.c_ulong), ('send_event', c.c_int),
        ('display', c.c_void_p), ('window', c.c_ulong), ('root', c.c_ulong),
        ('subwindow', c.c_ulong), ('time', c.c_ulong), ('x', c.c_int), ('y', c.c_int),
        ('x_root', c.c_int), ('y_root', c.c_int), ('state', c.c_uint),
        ('detail', c.c_uint), ('same_screen', c.c_int)]


class MotionEvent(c.Structure):
    _fields_ = KeyButtonEvent._fields_[:-2] + [('is_hint', c.c_char), ('same_screen', c.c_int)]


class FocusEvent(c.Structure):
    _fields_ = [('type', c.c_int), ('serial', c.c_ulong), ('send_event', c.c_int),
               ('display', c.c_void_p), ('window', c.c_ulong), ('mode', c.c_int), ('detail', c.c_int)]


class XEvent(c.Union):
    _fields_ = [('key', KeyButtonEvent), ('motion', MotionEvent), ('focus', FocusEvent), ('pad', c.c_long * 24)]


def gesture_points(gesture, width, height, frame_width, frame_height):
    """Stay in the central map area, respecting scrcpy's aspect-ratio margins."""
    scale = min(width / frame_width, height / frame_height)
    w, h = frame_width * scale, frame_height * scale
    ox, oy = (width - w) / 2, (height - h) / 2
    points = {
        WazeGesture.PAN_UP: ((.5, .43), (.5, .63)),
        WazeGesture.PAN_DOWN: ((.5, .63), (.5, .43)),
        WazeGesture.PAN_LEFT: ((.40, .53), (.60, .53)),
        WazeGesture.PAN_RIGHT: ((.60, .53), (.40, .53)),
        WazeGesture.ZOOM_IN: ((.58, .5), (.72, .5)),
        WazeGesture.ZOOM_OUT: ((.72, .5), (.58, .5)),
    }[gesture]
    return tuple((round(ox + x * w), round(oy + y * h)) for x, y in points)


def send(window, title, gesture, frame_size):
    lib = c.CDLL(find_library('X11') or 'libX11.so')
    lib.XOpenDisplay.argtypes, lib.XOpenDisplay.restype = [c.c_char_p], c.c_void_p
    lib.XDefaultRootWindow.argtypes, lib.XDefaultRootWindow.restype = [c.c_void_p], c.c_ulong
    lib.XFetchName.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_void_p)]
    lib.XInternAtom.argtypes, lib.XInternAtom.restype = [c.c_void_p, c.c_char_p, c.c_int], c.c_ulong
    lib.XGetWindowProperty.argtypes = [c.c_void_p, c.c_ulong, c.c_ulong, c.c_long, c.c_long,
        c.c_int, c.c_ulong, c.POINTER(c.c_ulong), c.POINTER(c.c_int), c.POINTER(c.c_ulong),
        c.POINTER(c.c_ulong), c.POINTER(c.c_void_p)]
    lib.XFree.argtypes = [c.c_void_p]
    lib.XGetGeometry.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_ulong), c.POINTER(c.c_int),
        c.POINTER(c.c_int), c.POINTER(c.c_uint), c.POINTER(c.c_uint), c.POINTER(c.c_uint), c.POINTER(c.c_uint)]
    lib.XSendEvent.argtypes = [c.c_void_p, c.c_ulong, c.c_int, c.c_long, c.POINTER(XEvent)]
    lib.XSync.argtypes = [c.c_void_p, c.c_int]
    lib.XKeysymToKeycode.argtypes, lib.XKeysymToKeycode.restype = [c.c_void_p, c.c_ulong], c.c_uint
    lib.XCloseDisplay.argtypes = [c.c_void_p]
    lib.XGetInputFocus.argtypes = [c.c_void_p, c.POINTER(c.c_ulong), c.POINTER(c.c_int)]
    display = lib.XOpenDisplay(None)
    if not display:
        raise RuntimeError('Could not open the viewer X11 display')
    root = lib.XDefaultRootWindow(display)
    name = c.c_void_p()
    name_atom = lib.XInternAtom(display, b'_NET_WM_NAME', 0)
    def identity_matches():
        actual, format_, items, remaining = c.c_ulong(), c.c_int(), c.c_ulong(), c.c_ulong()
        if lib.XGetWindowProperty(display, window, name_atom, 0, 1024, 0, 0,
            c.byref(actual), c.byref(format_), c.byref(items), c.byref(remaining), c.byref(name)) == 0 and name.value:
            try:
                return format_.value == 8 and c.string_at(name, items.value).decode() == title
            finally:
                lib.XFree(name)
        if not lib.XFetchName(display, window, c.byref(name)) or not name.value:
            return False
        try:
            return c.string_at(name).decode() == title
        finally:
            lib.XFree(name)
    ctrl_down = button_down = focus_sent = False
    point = (0, 0)
    expected_size = None
    ctrl = lib.XKeysymToKeycode(display, 0xffe3)
    def geometry():
        geometry_root, x, y = c.c_ulong(), c.c_int(), c.c_int()
        width, height, border, depth = (c.c_uint() for _ in range(4))
        if not lib.XGetGeometry(display, window, c.byref(geometry_root), c.byref(x), c.byref(y),
            c.byref(width), c.byref(height), c.byref(border), c.byref(depth)):
            raise RuntimeError('Viewer geometry unavailable')
        return width.value, height.value
    def event(kind, detail=0, state=0):
        if not identity_matches():
            raise RuntimeError('The owned viewer window changed')
        if kind in (4, 6) and expected_size is not None and geometry() != expected_size:
            raise RuntimeError('Viewer resized during the gesture; retry after layout settles')
        value = XEvent()
        target = value.motion if kind == 6 else value.key
        target.type, target.display, target.window, target.root = kind, display, window, root
        target.send_event, target.same_screen = 1, 1
        target.x, target.y = point
        target.state = state
        if kind != 6:
            target.detail = detail
        mask = {2: 1, 3: 2, 4: 4, 5: 8, 6: 64 | 256}[kind]
        if not lib.XSendEvent(display, window, 0, mask, c.byref(value)):
            raise RuntimeError('Viewer input could not be delivered')
        lib.XSync(display, 0)
    try:
        if not identity_matches():
            raise RuntimeError('The owned viewer window changed')
        expected_size = geometry()
        width, height = expected_size
        if width < 120 or height < 100:
            raise RuntimeError('Expand the Waze viewer before using gesture controls')
        focus = XEvent()
        focus.focus = FocusEvent(type=9, display=display, window=window, mode=0, detail=3)
        lib.XSendEvent(display, window, 0, 1 << 21, c.byref(focus))
        focus_sent = True
        lib.XSync(display, 0)
        time.sleep(.08)
        start, end = gesture_points(gesture, width, height, *frame_size)
        point = start
        pinch = gesture in (WazeGesture.ZOOM_IN, WazeGesture.ZOOM_OUT)
        if pinch:
            ctrl_down = True
            event(2, ctrl)
            time.sleep(.04)
        modifier = 4 if pinch else 0
        event(6, state=modifier)
        button_down = True
        event(4, 1, modifier)
        for step in range(1, 13):
            point = tuple(round(a + (b - a) * step / 12) for a, b in zip(start, end))
            event(6, state=modifier | 256)
            time.sleep(.016)
    finally:
        try:
            try:
                if button_down:
                    event(5, 1, (4 if ctrl_down else 0) | 256)
            finally:
                if ctrl_down:
                    event(3, ctrl, 4)
        finally:
            current, current_revert = c.c_ulong(), c.c_int()
            lib.XGetInputFocus(display, c.byref(current), c.byref(current_revert))
            if focus_sent and current.value != window and identity_matches():
                focus = XEvent()
                focus.focus = FocusEvent(type=10, display=display, window=window, mode=0, detail=3)
                lib.XSendEvent(display, window, 0, 1 << 21, c.byref(focus))
                lib.XSync(display, 0)
            lib.XCloseDisplay(display)


def main():
    value = json.loads(sys.stdin.read())
    def interrupted(_signal, _frame):
        raise InterruptedError('Gesture cancelled')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        send(value['window'], value['title'], WazeGesture(value['gesture']), value['frame_size'])
    except InterruptedError:
        pass  # Cancellation already released input in send()'s finally block.


if __name__ == '__main__':
    main()
