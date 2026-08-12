# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-side configuration for a radio session."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RadioSessionConfig:
    """Identify a session and provide its status/tuning defaults."""

    key: str
    title: str
    default_step_hz: int

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("key must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if self.default_step_hz <= 0:
            raise ValueError("default_step_hz must be greater than zero")
