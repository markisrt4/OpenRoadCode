from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum, auto
import logging
from queue import Empty, SimpleQueue
from typing import Any

from hardware_io.rotary_encoder import RotaryEncoderIf


LOGGER = logging.getLogger(__name__)

PanelRotationCallback = Callable[[int, int], None]
PanelButtonCallback = Callable[[int], None]


@dataclass(frozen=True, slots=True)
class PanelEncoderCallbacks:
    """Callbacks selected by the panel currently displayed in the Car UI."""

    rotated: PanelRotationCallback | None = None
    button_pressed: PanelButtonCallback | None = None
    button_released: PanelButtonCallback | None = None


class _EventKind(Enum):
    ROTATED = auto()
    BUTTON_PRESSED = auto()
    BUTTON_RELEASED = auto()


@dataclass(frozen=True, slots=True)
class _EncoderEvent:
    encoder_index: int
    kind: _EventKind
    panel_generation: int
    steps: int = 0


class EncoderEventRouter:
    """
    Move encoder callbacks onto the Tk thread and route them by role.

    The configured volume encoder is always routed to the global volume
    callbacks. All other encoders are routed to callbacks registered by the
    panel currently displayed.
    """

    DEFAULT_POLL_INTERVAL_MS = 10

    def __init__(
        self,
        *,
        root: Any,
        encoders: Sequence[RotaryEncoderIf],
        volume_encoder_index: int,
        volume_up: Callable[[], None],
        volume_down: Callable[[], None],
        volume_button_pressed: Callable[[], None] | None = None,
        poll_interval_ms: int = DEFAULT_POLL_INTERVAL_MS,
    ) -> None:
        if not encoders:
            raise ValueError("encoders must not be empty")
        if not 0 <= volume_encoder_index < len(encoders):
            raise ValueError(
                "volume_encoder_index must identify a configured encoder"
            )
        if poll_interval_ms <= 0:
            raise ValueError("poll_interval_ms must be greater than zero")

        self._root = root
        self._encoders = tuple(encoders)
        self._volume_encoder_index = volume_encoder_index
        self._panel_slots = {
            encoder_index: slot
            for slot, encoder_index in enumerate(
                index
                for index in range(len(self._encoders))
                if index != volume_encoder_index
            )
        }
        self._volume_up = volume_up
        self._volume_down = volume_down
        self._volume_button_pressed = volume_button_pressed
        self._poll_interval_ms = poll_interval_ms

        self._events: SimpleQueue[_EncoderEvent] = SimpleQueue()
        self._panel_callbacks = PanelEncoderCallbacks()
        self._panel_generation = 0
        self._after_id: str | None = None
        self._running = False
        self._active_encoder_indexes: set[int] = set()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def volume_encoder_index(self) -> int:
        return self._volume_encoder_index

    def set_panel_callbacks(
        self,
        callbacks: PanelEncoderCallbacks,
    ) -> None:
        self._panel_generation += 1
        self._panel_callbacks = callbacks

    def clear_panel_callbacks(self) -> None:
        self.set_panel_callbacks(PanelEncoderCallbacks())

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._active_encoder_indexes.clear()

        for encoder_index, encoder in enumerate(self._encoders):
            try:
                encoder.start(
                    rotated=self._rotation_callback(encoder_index),
                    button_pressed=self._button_callback(
                        encoder_index,
                        _EventKind.BUTTON_PRESSED,
                    ),
                    button_released=self._button_callback(
                        encoder_index,
                        _EventKind.BUTTON_RELEASED,
                    ),
                )
            except Exception as exc:
                LOGGER.warning(
                    "Rotary encoder unavailable at index %d: %s",
                    encoder_index,
                    exc,
                )
                continue

            self._active_encoder_indexes.add(encoder_index)

        self._schedule_poll()

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False

        if self._after_id is not None:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

        for encoder_index in self._active_encoder_indexes:
            try:
                self._encoders[encoder_index].stop()
            except Exception:
                LOGGER.exception(
                    "Rotary encoder stop failed for encoder index %d",
                    encoder_index,
                )
        self._active_encoder_indexes.clear()

        self.clear_panel_callbacks()
        self._discard_queued_events()

    def _rotation_callback(
        self,
        encoder_index: int,
    ) -> Callable[[int], None]:
        def rotated(steps: int) -> None:
            if self._running:
                self._events.put(
                    _EncoderEvent(
                        encoder_index=encoder_index,
                        kind=_EventKind.ROTATED,
                        steps=steps,
                        panel_generation=self._panel_generation,
                    )
                )

        return rotated

    def _button_callback(
        self,
        encoder_index: int,
        kind: _EventKind,
    ) -> Callable[[], None]:
        def button_event() -> None:
            if self._running:
                self._events.put(
                    _EncoderEvent(
                        encoder_index=encoder_index,
                        kind=kind,
                        panel_generation=self._panel_generation,
                    )
                )

        return button_event

    def _schedule_poll(self) -> None:
        if self._running:
            self._after_id = self._root.after(
                self._poll_interval_ms,
                self._poll_events,
            )

    def _poll_events(self) -> None:
        self._after_id = None

        if not self._running:
            return

        for encoder_index in self._active_encoder_indexes:
            encoder = self._encoders[encoder_index]
            try:
                encoder.poll()
            except Exception:
                LOGGER.exception(
                    "Rotary encoder poll failed for encoder index %d",
                    encoder_index,
                )

        while True:
            try:
                event = self._events.get_nowait()
            except Empty:
                break

            try:
                self._dispatch(event)
            except Exception:
                LOGGER.exception(
                    "Panel encoder callback failed for encoder index %d",
                    event.encoder_index,
                )

        self._schedule_poll()

    def _dispatch(self, event: _EncoderEvent) -> None:
        if event.encoder_index == self._volume_encoder_index:
            if event.kind is _EventKind.ROTATED:
                callback = (
                    self._volume_up
                    if event.steps > 0
                    else self._volume_down
                )
                for _ in range(abs(event.steps)):
                    callback()
            elif (
                event.kind is _EventKind.BUTTON_PRESSED
                and self._volume_button_pressed is not None
            ):
                self._volume_button_pressed()
            return

        if event.panel_generation != self._panel_generation:
            return

        callbacks = self._panel_callbacks
        slot = self._panel_slots[event.encoder_index]

        if event.kind is _EventKind.ROTATED:
            if callbacks.rotated is not None:
                callbacks.rotated(slot, event.steps)
        elif event.kind is _EventKind.BUTTON_PRESSED:
            if callbacks.button_pressed is not None:
                callbacks.button_pressed(slot)
        elif callbacks.button_released is not None:
            callbacks.button_released(slot)

    def _discard_queued_events(self) -> None:
        while True:
            try:
                self._events.get_nowait()
            except Empty:
                return
