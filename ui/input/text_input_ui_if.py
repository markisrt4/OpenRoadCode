# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Immutable text-input presentation state; typed contents stay in the target."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TextInputState:
    session_id: int | None = None
    keyboard_available: bool = False
    keyboard_requested: bool = False
    error: str | None = None
    closed: bool = False


class TextInputUiIf(Protocol):
    def set_text_input_state(self, state: TextInputState) -> None:
        """Replace the full input-session presentation state."""
        ...
