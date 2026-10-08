"""Native X11 presentation adapter for a circular floating control."""

import ctypes
from ctypes.util import find_library
import math


class _Rectangle(ctypes.Structure):
    _fields_ = [("x", ctypes.c_short), ("y", ctypes.c_short),
                ("width", ctypes.c_ushort), ("height", ctypes.c_ushort)]


def shape_circle(window_id: int, diameter: int) -> bool:
    """Clip an X11 client and its Tk wrapper; no compositor is required."""
    try:
        x11 = ctypes.CDLL(find_library("X11") or "libX11.so")
        extension = ctypes.CDLL(find_library("Xext") or "libXext.so")
    except OSError:
        return False
    pointer, xid = ctypes.c_void_p, ctypes.c_ulong
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = pointer
    x11.XCloseDisplay.argtypes = [pointer]
    x11.XSync.argtypes = [pointer, ctypes.c_int]
    x11.XFree.argtypes = [pointer]
    x11.XQueryTree.argtypes = [pointer, xid, ctypes.POINTER(xid), ctypes.POINTER(xid),
                              ctypes.POINTER(ctypes.POINTER(xid)), ctypes.POINTER(ctypes.c_uint)]
    extension.XShapeQueryExtension.argtypes = [pointer, ctypes.POINTER(ctypes.c_int),
                                              ctypes.POINTER(ctypes.c_int)]
    extension.XShapeCombineRectangles.argtypes = [pointer, xid, ctypes.c_int, ctypes.c_int,
                                                 ctypes.c_int, ctypes.POINTER(_Rectangle),
                                                 ctypes.c_int, ctypes.c_int, ctypes.c_int]
    display = x11.XOpenDisplay(None)
    if not display:
        return False
    try:
        event, error = ctypes.c_int(), ctypes.c_int()
        if not extension.XShapeQueryExtension(display, ctypes.byref(event), ctypes.byref(error)):
            return False
        radius = diameter / 2
        rows = []
        for y in range(diameter):
            half = math.sqrt(max(0, radius**2 - (y + .5 - radius)**2))
            left, right = math.ceil(radius - half), math.floor(radius + half)
            rows.append(_Rectangle(left, y, max(0, right - left), 1))
        rectangles = (_Rectangle * len(rows))(*rows)
        root, parent = xid(), xid()
        children, count = ctypes.POINTER(xid)(), ctypes.c_uint()
        windows = [window_id]
        if x11.XQueryTree(display, window_id, ctypes.byref(root), ctypes.byref(parent),
                          ctypes.byref(children), ctypes.byref(count)):
            if children:
                x11.XFree(children)
            if parent.value and parent.value != root.value:
                windows.append(parent.value)
        for window in windows:
            # ShapeBounding + ShapeSet + YXBanded. Bounding also clips input.
            extension.XShapeCombineRectangles(display, window, 0, 0, 0,
                                              rectangles, len(rows), 0, 3)
        x11.XSync(display, 0)
        return True
    finally:
        x11.XCloseDisplay(display)
