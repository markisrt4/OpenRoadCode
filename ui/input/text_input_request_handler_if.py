# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Semantic requests for one active text-entry session."""

from typing import Protocol

from ui.input.text_input_target_if import TextInputTargetIf


class TextInputRequestHandlerIf(Protocol):
    def request_begin(self, target: TextInputTargetIf) -> int | None:
        """Focus a target and return its session token, or None if closed/failed.

        @param target Text target receiving focus and input.
        @return Session token, or None if the request failed or the handler is closed.
        """
        ...

    def request_show_keyboard(self, session_id: int) -> None:
        """Show the system keyboard for this session.

        @param session_id Token identifying the active text-input session.
        """
        ...

    def request_hide_keyboard(self, session_id: int) -> None:
        """Hide the keyboard while retaining the current text-entry session.

        @param session_id Token identifying the active text-input session.
        """
        ...

    def request_submit(self, session_id: int) -> None:
        """Submit and release this session.

        @param session_id Token identifying the active text-input session.
        """
        ...

    def request_cancel(self, session_id: int) -> None:
        """Cancel and release this session.

        @param session_id Token identifying the active text-input session.
        """
        ...
