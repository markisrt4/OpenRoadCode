"""Verify native clipping, including the wrapper outside Tk's client window."""

import ctypes
from ctypes.util import find_library
import tkinter as tk
import unittest

from frontends.x11.circular_window import shape_circle, _Rectangle


class CircularWindowTest(unittest.TestCase):
    def test_x_server_excludes_corners_but_keeps_centre_on_client_and_wrapper(self):
        try:
            root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(root.destroy)
        root.geometry("46x46")
        root.update()
        self.assertTrue(shape_circle(root.winfo_id(), 46))
        x11 = ctypes.CDLL(find_library("X11") or "libX11.so")
        ext = ctypes.CDLL(find_library("Xext") or "libXext.so")
        pointer, xid = ctypes.c_void_p, ctypes.c_ulong
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = pointer
        x11.XCloseDisplay.argtypes = [pointer]
        x11.XFree.argtypes = [pointer]
        x11.XQueryTree.argtypes = [pointer, xid, ctypes.POINTER(xid), ctypes.POINTER(xid),
                                  ctypes.POINTER(ctypes.POINTER(xid)), ctypes.POINTER(ctypes.c_uint)]
        ext.XShapeGetRectangles.argtypes = [pointer, xid, ctypes.c_int,
                                           ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        ext.XShapeGetRectangles.restype = ctypes.POINTER(_Rectangle)
        display = x11.XOpenDisplay(None)
        self.assertTrue(display)
        self.addCleanup(x11.XCloseDisplay, display)
        parent, server_root = xid(), xid()
        children, count = ctypes.POINTER(xid)(), ctypes.c_uint()
        self.assertTrue(x11.XQueryTree(display, root.winfo_id(), ctypes.byref(server_root),
                                      ctypes.byref(parent), ctypes.byref(children), ctypes.byref(count)))
        if children:
            x11.XFree(children)
        self.assertNotEqual(parent.value, server_root.value)
        for window in (root.winfo_id(), parent.value):
            count, ordering = ctypes.c_int(), ctypes.c_int()
            rectangles = ext.XShapeGetRectangles(display, window, 0, ctypes.byref(count),
                                                 ctypes.byref(ordering))
            try:
                def contains(x, y):
                    return any(r.x <= x < r.x + r.width and r.y <= y < r.y + r.height
                               for r in rectangles[:count.value])
                self.assertFalse(contains(0, 0))
                self.assertFalse(contains(45, 45))
                self.assertTrue(contains(23, 23))
            finally:
                x11.XFree(rectangles)
