# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Text-entry session ownership independent of GUI and keyboard implementation."""
from dataclasses import replace
from typing import Any

from hardware_io.keyboard.soft_keyboard_if import SoftKeyboardIf
from ui.input.text_input_request_handler_if import TextInputRequestHandlerIf
from ui.input.text_input_target_if import TextInputTargetIf
from ui.input.text_input_ui_if import TextInputState, TextInputUiIf


class TextInputController(TextInputRequestHandlerIf):
    """Serialize requests on the UI dispatch thread; reject retired session tokens.

    Targets own their text and native/browser submit behavior. Rebinding a field
    retires the previous session without submitting, cancelling, or erasing it.
    Composition closes this controller before destroying its target adapters.
    """

    def __init__(self, keyboard: SoftKeyboardIf) -> None:
        self._keyboard = keyboard
        self._state = TextInputState()
        self._target: TextInputTargetIf | None = None
        self._view: TextInputUiIf | None = None
        self._next_session = 0

    @property
    def state(self) -> TextInputState:
        return self._state

    def set_ui(self, view: TextInputUiIf | None) -> None:
        self._view = view
        if view is not None:
            view.set_text_input_state(self._state)

    def _publish(self, **changes: Any) -> None:
        self._state = replace(self._state, **changes)
        if self._view is not None:
            self._view.set_text_input_state(self._state)

    def _current(self, session_id: int) -> bool:
        return (
            not self._state.closed and self._state.session_id == session_id
            and self._target is not None
        )

    def request_begin(self, target: TextInputTargetIf) -> int | None:
        if self._state.closed:
            return None
        if self._state.keyboard_requested:
            try:
                self._keyboard.hide()
            except Exception:
                self._publish(error='Could not hide the system keyboard')
                return None
        self._target = None
        self._next_session += 1
        session_id = self._next_session
        self._publish(session_id=session_id, keyboard_requested=False, error=None)
        if self._state.session_id != session_id or self._state.closed:
            return None
        try:
            available = self._keyboard.available
            target.focus()
        except Exception:
            if self._state.session_id == session_id:
                self._publish(session_id=None, error='Could not prepare text input')
            return None
        if self._state.session_id != session_id or self._state.closed:
            return None
        self._target = target
        self._publish(keyboard_available=available)
        return session_id

    def request_show_keyboard(self, session_id: int) -> None:
        if not self._current(session_id):
            return
        target = self._target
        assert target is not None
        try:
            available = self._keyboard.available
            if not available:
                self._publish(keyboard_available=False, error='System keyboard unavailable')
                return
            self._keyboard.show()
            # Restore field focus through its supplied native/browser contract.
            if not self._current(session_id):
                return
            self._publish(keyboard_available=True, keyboard_requested=True, error=None)
            if self._current(session_id):
                target.focus()
        except Exception:
            if self._current(session_id):
                try:
                    self._keyboard.hide()
                except Exception:
                    self._publish(keyboard_requested=True, error='Could not release the system keyboard')
                    return
                self._publish(keyboard_requested=False, error='Could not show the system keyboard')
            return
        if self._current(session_id):
            self._publish(keyboard_available=True, keyboard_requested=True, error=None)

    def request_hide_keyboard(self, session_id: int) -> None:
        if not self._current(session_id):
            return
        try:
            self._keyboard.hide()
        except Exception:
            self._publish(error='Could not hide the system keyboard')
            return
        self._publish(keyboard_requested=False, error=None)

    def _finish(self, session_id: int, *, submit: bool) -> None:
        if not self._current(session_id):
            return
        target = self._target
        assert target is not None
        try:
            if submit:
                target.submit()
            else:
                target.cancel()
        except Exception:
            if self._current(session_id):
                self._publish(error='Could not complete text input')
            return
        # A target's submit/cancel callback may already have opened another field.
        if self._current(session_id):
            self.request_hide_keyboard(session_id)
            self._target = None
            self._publish(session_id=None)

    def request_submit(self, session_id: int) -> None:
        self._finish(session_id, submit=True)

    def request_cancel(self, session_id: int) -> None:
        self._finish(session_id, submit=False)

    def close(self) -> None:
        if self._state.closed:
            return
        self._target = None
        self._publish(closed=True, session_id=None)
        try:
            self._keyboard.close()
        except Exception:
            self._publish(error='Could not close the system keyboard')
            raise
        else:
            self._publish(keyboard_available=False, keyboard_requested=False, error=None)
        finally:
            self._view = None
