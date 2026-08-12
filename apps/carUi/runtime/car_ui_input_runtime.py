# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Car UI ownership and polling for configured physical input devices."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
import logging

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
    InputHandlerIf,
)
from controllers.input import (
    RotaryEncoderInputAdapter,
)
from frontends.common.input import UiInputEventDispatcher
from hardware_io.rotary_encoder import RotaryEncoderIf
from hardware_io.buttons.push_button_if import PushButtonIf
from hardware_io.keyboard import KeyboardReaderIf
from ui import UiDispatcherIf


LOGGER = logging.getLogger(__name__)


class _InputAdapter(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...


class CarUiInputRuntime:
    """Own input adapters and service them from the frontend event loop.

    Device connection failures are isolated so remaining configured devices
    continue operating. Physical events are queued and delivered only when the
    frontend dispatcher runs the polling callback.
    """

    DEFAULT_POLL_INTERVAL_MS = 10

    def __init__(
        self,
        *,
        dispatcher: UiDispatcherIf,
        encoders: Sequence[RotaryEncoderIf],
        device_ids: Sequence[InputDeviceId],
        input_handler: InputHandlerIf,
        keyboards: Sequence[KeyboardReaderIf] = (),
        push_buttons: Sequence[PushButtonIf] = (),
        poll_interval_ms: int = DEFAULT_POLL_INTERVAL_MS,
    ) -> None:
        if not encoders:
            raise ValueError("encoders must not be empty")
        if len(device_ids) != len(encoders):
            raise ValueError("device_ids must identify every configured encoder")
        if len(set(device_ids)) != len(device_ids):
            raise ValueError("device_ids must be unique")
        if poll_interval_ms <= 0:
            raise ValueError("poll_interval_ms must be greater than zero")

        self._dispatcher = dispatcher
        self._event_dispatcher = UiInputEventDispatcher(
            _StepExpandingInputHandler(input_handler)
        )
        self._adapters = tuple(
            RotaryEncoderInputAdapter(encoder, device_id, self._event_dispatcher)
            for encoder, device_id in zip(encoders, device_ids)
        )
        from controllers.input import KeyboardInputAdapter, PushButtonInputAdapter

        self._additional_adapters: tuple[_InputAdapter, ...] = (
            *(
                KeyboardInputAdapter(
                    keyboard,
                    InputDeviceId(InputDeviceType.KEYBOARD, index),
                    self._event_dispatcher,
                )
                for index, keyboard in enumerate(keyboards)
            ),
            *(
                PushButtonInputAdapter(
                    button,
                    InputDeviceId(InputDeviceType.PUSHBUTTON, index),
                    self._event_dispatcher,
                )
                for index, button in enumerate(push_buttons)
            ),
        )
        self._poll_interval_ms = poll_interval_ms
        self._active_indexes: set[int] = set()
        self._active_additional_indexes: set[int] = set()
        self._callback_id: object | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Return whether input polling is active.

        @return True after start() and before stop().
        """
        return self._running

    def start(self) -> None:
        """Connect available devices and begin frontend-thread polling."""
        if self._running:
            return
        self._running = True
        for index, adapter in enumerate(self._adapters):
            try:
                adapter.connect()
            except Exception as exc:
                LOGGER.warning("Rotary encoder unavailable at index %d: %s", index, exc)
                continue
            self._active_indexes.add(index)
        for index, adapter in enumerate(self._additional_adapters):
            try:
                adapter.connect()
            except Exception as exc:
                LOGGER.warning("Input device unavailable at index %d: %s", index, exc)
                continue
            self._active_additional_indexes.add(index)
        self._schedule_poll()

    def stop(self) -> None:
        """Stop polling, disconnect active adapters, and discard queued input."""
        if not self._running:
            return
        self._running = False
        if self._callback_id is not None:
            try:
                self._dispatcher.cancel_ui_callback(self._callback_id)
            except Exception:
                pass
            self._callback_id = None
        for index in self._active_indexes:
            try:
                self._adapters[index].disconnect()
            except Exception:
                LOGGER.exception("Rotary encoder stop failed for encoder index %d", index)
        self._active_indexes.clear()
        for index in self._active_additional_indexes:
            try:
                self._additional_adapters[index].disconnect()
            except Exception:
                LOGGER.exception("Input device stop failed for index %d", index)
        self._active_additional_indexes.clear()
        self._event_dispatcher.discard_pending()

    def _schedule_poll(self) -> None:
        if self._running:
            self._callback_id = self._dispatcher.schedule_ui_callback(
                self._poll_interval_ms, self._poll
            )

    def _poll(self) -> None:
        self._callback_id = None
        if not self._running:
            return
        for index in self._active_indexes:
            try:
                self._adapters[index].poll()
            except Exception:
                LOGGER.exception("Rotary encoder poll failed for encoder index %d", index)
        self._event_dispatcher.dispatch_pending()
        self._schedule_poll()


class _StepExpandingInputHandler(InputHandlerIf):
    """Preserve one semantic navigation action per encoder detent."""

    def __init__(self, target: InputHandlerIf) -> None:
        self._target = target

    def handle_input_event(self, event: InputEvent) -> None:
        """Forward an event, expanding multi-detent rotation into unit steps.

        @param event Normalized physical input event to forward.
        """
        if event.event_type is not InputEventType.ROTATED:
            self._target.handle_input_event(event)
            return
        steps = event.value if isinstance(event.value, int) else 0
        direction = 1 if steps > 0 else -1
        for _ in range(abs(steps)):
            self._target.handle_input_event(
                InputEvent(event.device_id, event.event_type, direction)
            )
