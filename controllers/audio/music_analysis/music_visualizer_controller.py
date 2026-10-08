# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Reusable asynchronous capture coordination and bounded presentation."""
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import queue

from ui.music_visualizer import MusicVisualizerSource, VisualizerFrame
from ui.music_visualizer.music_visualizer_control_if import MusicVisualizerControlIf
from .music_visualizer_session import MusicVisualizerSession


class MusicVisualizerController(MusicVisualizerControlIf):
    """Own backend workers independently of a concrete frontend or application."""

    def __init__(self, session_factory: Callable[..., MusicVisualizerSession | None]) -> None:
        self._session_factory = session_factory
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="music-visualizer")
        self._session: MusicVisualizerSession | None = None
        self._frames: queue.Queue[tuple[int, VisualizerFrame]] = queue.Queue(maxsize=1)
        self._messages: queue.SimpleQueue[tuple[int, str]] = queue.SimpleQueue()
        self._generation = 0
        self._connected_generation: int | None = None
        self._closed = False

    def start(self, source: MusicVisualizerSource) -> None:
        if self._closed:
            return
        self._generation += 1
        self._connected_generation = None
        self._executor.submit(self._start_capture, self._generation, source)

    def stop(self) -> None:
        if self._closed:
            return
        self._generation += 1
        self._connected_generation = None
        self._executor.submit(self._release_capture)

    def _offer_frame(self, generation: int, frame: VisualizerFrame) -> None:
        if generation != self._generation:
            return
        try:
            self._frames.get_nowait()
        except queue.Empty:
            pass
        try:
            self._frames.put_nowait((generation, frame))
        except queue.Full:
            pass

    def _start_capture(self, generation: int, source: MusicVisualizerSource) -> None:
        self._release_capture()
        if generation != self._generation:
            return
        try:
            self._session = self._session_factory(
                lambda frame: self._offer_frame(generation, frame), source=source,
            )
            if self._session is not None:
                self._session.start()
                self._connected_generation = generation
                self._messages.put((generation, "Audio input connected"))
        except Exception as exc:
            self._release_capture()
            self._messages.put((generation, f"Audio input unavailable: {exc}"))
        finally:
            if generation != self._generation:
                self._release_capture()

    def _release_capture(self) -> None:
        session, self._session = self._session, None
        if session is not None:
            session.close()

    def calibrate(self, action: str) -> None:
        if self._closed:
            return
        if action not in {"start_zeroize", "finish_zeroize", "clear_zeroize"}:
            raise ValueError("Unknown calibration action")
        generation = self._generation
        def run() -> None:
            if generation != self._generation:
                return
            try:
                if self._session is None:
                    raise RuntimeError("Start a real audio input before calibration")
                getattr(self._session, action)()
                messages = {"start_zeroize": "Collecting ambient noise — press FINISH when ready",
                            "finish_zeroize": "Noise calibration saved",
                            "clear_zeroize": "Noise calibration cleared"}
                self._messages.put((generation, messages[action]))
            except Exception as exc:
                self._messages.put((generation, f"Calibration unavailable: {exc}"))
        self._executor.submit(run)

    def presentation(self) -> tuple[VisualizerFrame | None, str | None]:
        frame = None
        message = None
        try:
            generation, candidate = self._frames.get_nowait()
            if generation == self._generation:
                frame = candidate
        except queue.Empty:
            pass
        while True:
            try:
                generation, candidate_message = self._messages.get_nowait()
            except queue.Empty:
                break
            if generation == self._generation:
                message = candidate_message
        if (self._connected_generation == self._generation
                and self._session is not None and not self._session.is_running):
            message = "Audio input stopped — check the source and press START"
        return frame, message

    def close(self) -> None:
        if self._closed:
            return
        self.stop()
        self._closed = True
        self._executor.shutdown(wait=True)
