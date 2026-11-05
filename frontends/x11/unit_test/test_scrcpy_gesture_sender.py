# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Verify the SDL events scrcpy consumes, plus unchanged real pointer/focus."""
import ctypes as c
from ctypes.util import find_library
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from frontends.x11.scrcpy_gesture_sender import gesture_points
from ui.navigation.waze_gesture_if import WazeGesture


def test_pan_directions_move_view_not_finger_and_keep_points_inside_letterboxed_map():
    start, end = gesture_points(WazeGesture.PAN_UP, 400, 300, 1280, 720)
    assert end[1] > start[1]
    start, end = gesture_points(WazeGesture.PAN_LEFT, 400, 300, 1280, 720)
    assert end[0] > start[0]
    for gesture in WazeGesture:
        for x, y in gesture_points(gesture, 400, 300, 1280, 720):
            assert 0 < x < 400 and 38 < y < 262


@pytest.mark.skipif(not os.environ.get('DISPLAY') or not find_library('SDL2-2.0'), reason='SDL2 and X11 required')
@pytest.mark.parametrize('gesture,mode', [(WazeGesture.ZOOM_IN, 'complete'), (WazeGesture.PAN_UP, 'complete'),
    (WazeGesture.ZOOM_IN, 'cancel'), (WazeGesture.ZOOM_IN, 'wrong-title')])
def test_real_sdl_receives_drag_and_pinch_without_global_pointer_or_focus_change(monkeypatch, gesture, mode):
    monkeypatch.setenv('SDL_MOUSE_AUTO_CAPTURE', '0')
    monkeypatch.setenv('SDL_VIDEODRIVER', 'x11')
    sdl = c.CDLL(find_library('SDL2-2.0'))
    sdl.SDL_CreateWindow.argtypes = [c.c_char_p, c.c_int, c.c_int, c.c_int, c.c_int, c.c_uint]
    sdl.SDL_CreateWindow.restype = c.c_void_p
    sdl.SDL_GetWindowWMInfo.argtypes = [c.c_void_p, c.c_void_p]
    sdl.SDL_DestroyWindow.argtypes = [c.c_void_p]
    sdl.SDL_PollEvent.argtypes = [c.c_void_p]
    sdl.SDL_GetModState.restype = c.c_uint16
    assert sdl.SDL_Init(32) == 0
    title = 'ORC gesture event receiver'
    window = sdl.SDL_CreateWindow(title.encode(), 0, 0, 400, 300, 4)
    assert window

    class Info(c.Structure):
        _fields_ = [('version', c.c_ubyte * 3), ('subsystem', c.c_int), ('data', c.c_ulong * 8)]

    info = Info()
    sdl.SDL_GetVersion(c.byref(info.version))
    assert sdl.SDL_GetWindowWMInfo(window, c.byref(info))
    xid = info.data[1]
    lib = c.CDLL(find_library('X11'))
    lib.XOpenDisplay.restype = c.c_void_p
    display = lib.XOpenDisplay(None)
    lib.XDefaultRootWindow.argtypes, lib.XDefaultRootWindow.restype = [c.c_void_p], c.c_ulong
    lib.XGetInputFocus.argtypes = [c.c_void_p, c.POINTER(c.c_ulong), c.POINTER(c.c_int)]
    lib.XQueryPointer.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_ulong), c.POINTER(c.c_ulong),
        c.POINTER(c.c_int), c.POINTER(c.c_int), c.POINTER(c.c_int), c.POINTER(c.c_int), c.POINTER(c.c_uint)]
    lib.XCloseDisplay.argtypes = [c.c_void_p]

    def real_input():
        focus, revert = c.c_ulong(), c.c_int()
        lib.XGetInputFocus(display, c.byref(focus), c.byref(revert))
        root, child, x, y, wx, wy, state = c.c_ulong(), c.c_ulong(), c.c_int(), c.c_int(), c.c_int(), c.c_int(), c.c_uint()
        lib.XQueryPointer(display, lib.XDefaultRootWindow(display), c.byref(root), c.byref(child),
                          c.byref(x), c.byref(y), c.byref(wx), c.byref(wy), c.byref(state))
        return focus.value, x.value, y.value, state.value

    events = (c.c_uint32 * 14)()
    process = None
    try:
        for _ in range(50):
            while sdl.SDL_PollEvent(c.byref(events)):
                pass
            time.sleep(.01)
        before = real_input()
        process = subprocess.Popen([sys.executable, '-m', 'frontends.x11.scrcpy_gesture_sender'],
            cwd=Path(__file__).resolve().parents[3], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        process.stdin.write(json.dumps(dict(window=xid, title=title if mode != 'wrong-title' else 'retired viewer',
                                           frame_size=[400, 300], gesture=gesture.value)))
        process.stdin.close()
        pressed, released, motion, ctrl_at_press, last_motion = False, False, 0, False, None
        cancelled = False
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            while sdl.SDL_PollEvent(c.byref(events)):
                if events[0] == 0x401:
                    pressed, ctrl_at_press = True, bool(sdl.SDL_GetModState() & 64)
                    if mode == 'cancel' and not cancelled:
                        cancelled = True
                        process.terminate()
                elif events[0] == 0x402:
                    released = True
                elif events[0] == 0x400:
                    motion += 1
                    last_motion = (events[5], events[6])
            if process.poll() is not None:
                break
            time.sleep(.002)
        code = process.wait(timeout=1)
        assert (code != 0) if mode == 'wrong-title' else code == 0, process.stderr.read()
        if mode == 'wrong-title':
            assert not pressed and not released
        else:
            assert pressed and released
            assert motion >= 10 if mode == 'complete' else cancelled
            assert ctrl_at_press == (gesture is WazeGesture.ZOOM_IN)
            if mode == 'complete':
                assert last_motion == gesture_points(gesture, 400, 300, 400, 300)[1]
        assert sdl.SDL_GetModState() & 64 == 0
        assert real_input() == before
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=2)
        lib.XCloseDisplay(display)
        sdl.SDL_DestroyWindow(window)
        sdl.SDL_Quit()
