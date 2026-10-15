# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Slow consumers skip frames without blocking the live stream reader."""

from queue import Queue
from threading import Event, Thread

import pytest

from hardware_io.camera.camera_if import CameraFrame
from hardware_io.camera.latest_frame_camera import LatestFrameCamera


class Source:
    def __init__(self):
        self.frames = Queue()
        self.is_open = False

    def open(self):
        self.is_open = True

    def read(self):
        item = self.frames.get(timeout=1)
        if isinstance(item, Exception):
            raise item
        frame, consumed = item
        consumed.set()
        return frame

    def close(self):
        if self.is_open:
            self.is_open = False
            self.frames.put(RuntimeError("source closed"))


def send(camera, source, sequence):
    consumed = Event()
    frame = CameraFrame(sequence, float(sequence), sequence)
    source.frames.put((frame, consumed))
    assert consumed.wait(1)
    # Wait for publication, not just the source's read completion.
    with camera._condition:
        assert camera._condition.wait_for(
            lambda: camera._latest is not None and camera._latest.sequence == sequence, timeout=1)
    return frame


def test_slow_consumer_gets_newest_frame_and_next_read_waits_for_new_pixels():
    source = Source()
    camera = LatestFrameCamera(source)
    camera.open()
    try:
        for sequence in range(20):
            newest = send(camera, source, sequence)
        assert camera.read() is newest
        delivered = []
        waiting = Thread(target=lambda: delivered.append(camera.read()))
        waiting.start()
        assert delivered == []
        next_frame = CameraFrame(20, 20.0, 20)
        source.frames.put((next_frame, Event()))
        waiting.join(1)
        assert not waiting.is_alive()
        assert delivered == [next_frame]
    finally:
        camera.close()


def test_close_unblocks_waiting_consumer_and_reopen_discards_previous_session():
    source = Source()
    camera = LatestFrameCamera(source)
    camera.open()
    errors = []

    def read():
        try:
            camera.read()
        except RuntimeError as error:
            errors.append(str(error))

    waiting = Thread(target=read)
    waiting.start()
    camera.close()
    waiting.join(1)
    assert not waiting.is_alive()
    assert errors == ["Camera read was cancelled"]
    assert not camera.is_open
    camera.open()
    try:
        newest = send(camera, source, 99)
        assert camera.read() is newest
    finally:
        camera.close()


def test_stream_failure_is_reported_instead_of_replaying_last_frame():
    source = Source()
    camera = LatestFrameCamera(source)
    camera.open()
    try:
        send(camera, source, 1)
        source.frames.put(RuntimeError("stream timed out"))
        with camera._condition:
            assert camera._condition.wait_for(lambda: camera._error is not None, timeout=1)
        with pytest.raises(RuntimeError, match="stream timed out"):
            camera.read()
    finally:
        camera.close()
