# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility exports for input values now owned by :mod:`input_events`."""

from input_events.input_event import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
)

__all__ = ["InputDeviceId", "InputDeviceType", "InputEvent", "InputEventType"]
