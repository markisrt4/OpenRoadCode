# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from hardware_io.automotive.elm327.elm327_errors import (
    Elm327CommandError,
    Elm327ConnectionError,
    Elm327Error,
)
from hardware_io.automotive.elm327.elm327_response import Elm327Response
from hardware_io.automotive.elm327.elm327_tcp_device import Elm327TcpDevice

try:
    from hardware_io.automotive.elm327.elm327_device import Elm327Device
except ModuleNotFoundError as exc:
    if exc.name != "serial":
        raise
    Elm327Device = None  # type: ignore[assignment,misc]

__all__ = [
    "Elm327CommandError",
    "Elm327ConnectionError",
    "Elm327Device",
    "Elm327Error",
    "Elm327Response",
    "Elm327TcpDevice",
]
