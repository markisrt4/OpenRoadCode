# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Embed an existing X11 client window inside another X11 window."""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import time


class X11WindowEmbedderError(RuntimeError):
    """Raised when an X11 window cannot be located or embedded."""


class X11WindowEmbedder:
    """Small libX11 wrapper used to reparent application windows into ORC UI."""

    def __init__(self, display: str | None = None) -> None:
        self.display_name = display or os.getenv("DISPLAY")
        if not self.display_name:
            raise X11WindowEmbedderError("DISPLAY is not set")

        library = ctypes.util.find_library("X11")
        if library is None:
            raise X11WindowEmbedderError("Could not find libX11")

        self._x11 = ctypes.CDLL(library)
        self._configure_functions()
        self._display = self._x11.XOpenDisplay(self.display_name.encode())
        if not self._display:
            raise X11WindowEmbedderError(
                f"Could not open X11 display {self.display_name}"
            )

    def close(self) -> None:
        if self._display:
            self._x11.XCloseDisplay(self._display)
            self._display = None

    def __enter__(self) -> "X11WindowEmbedder":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def find_window(
        self,
        *,
        title_contains: str,
        timeout_seconds: float = 10.0,
    ) -> int:
        """Wait for a top-level window whose title contains the requested text."""
        deadline = time.monotonic() + timeout_seconds
        needle = title_contains.casefold()
        while time.monotonic() < deadline:
            window = self._find_window_recursive(self._root_window(), needle)
            if window is not None:
                return window
            time.sleep(0.1)
        raise X11WindowEmbedderError(
            f"Timed out waiting for X11 window containing {title_contains!r}"
        )

    def embed(self, child_window: int, host_window: int) -> None:
        """Reparent and map child_window inside host_window."""
        self._x11.XUnmapWindow(self._display, child_window)
        self._x11.XReparentWindow(
            self._display,
            child_window,
            host_window,
            0,
            0,
        )
        self._x11.XMapWindow(self._display, child_window)
        self._x11.XFlush(self._display)

    def resize(self, child_window: int, width: int, height: int) -> None:
        """Resize an embedded client to fill its host."""
        if width <= 0 or height <= 0:
            return
        self._x11.XMoveResizeWindow(
            self._display,
            child_window,
            0,
            0,
            width,
            height,
        )
        self._x11.XFlush(self._display)

    def _root_window(self) -> int:
        return int(self._x11.XDefaultRootWindow(self._display))

    def _find_window_recursive(self, window: int, needle: str) -> int | None:
        title = self._window_title(window)
        if title is not None and needle in title.casefold():
            return window

        root = ctypes.c_ulong()
        parent = ctypes.c_ulong()
        children = ctypes.POINTER(ctypes.c_ulong)()
        child_count = ctypes.c_uint()
        result = self._x11.XQueryTree(
            self._display,
            window,
            ctypes.byref(root),
            ctypes.byref(parent),
            ctypes.byref(children),
            ctypes.byref(child_count),
        )
        if not result:
            return None

        try:
            for index in range(child_count.value):
                found = self._find_window_recursive(int(children[index]), needle)
                if found is not None:
                    return found
        finally:
            if children:
                self._x11.XFree(children)
        return None

    def _window_title(self, window: int) -> str | None:
        name = ctypes.c_char_p()
        if not self._x11.XFetchName(self._display, window, ctypes.byref(name)):
            return None
        if not name.value:
            return None
        try:
            return name.value.decode(errors="replace")
        finally:
            self._x11.XFree(name)

    def _configure_functions(self) -> None:
        display_ptr = ctypes.c_void_p
        window = ctypes.c_ulong

        self._x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self._x11.XOpenDisplay.restype = display_ptr
        self._x11.XCloseDisplay.argtypes = [display_ptr]
        self._x11.XDefaultRootWindow.argtypes = [display_ptr]
        self._x11.XDefaultRootWindow.restype = window
        self._x11.XFetchName.argtypes = [display_ptr, window, ctypes.POINTER(ctypes.c_char_p)]
        self._x11.XQueryTree.argtypes = [
            display_ptr,
            window,
            ctypes.POINTER(window),
            ctypes.POINTER(window),
            ctypes.POINTER(ctypes.POINTER(window)),
            ctypes.POINTER(ctypes.c_uint),
        ]
        self._x11.XReparentWindow.argtypes = [display_ptr, window, window, ctypes.c_int, ctypes.c_int]
        self._x11.XMoveResizeWindow.argtypes = [display_ptr, window, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
        self._x11.XMapWindow.argtypes = [display_ptr, window]
        self._x11.XUnmapWindow.argtypes = [display_ptr, window]
        self._x11.XFlush.argtypes = [display_ptr]
        self._x11.XFree.argtypes = [ctypes.c_void_p]
