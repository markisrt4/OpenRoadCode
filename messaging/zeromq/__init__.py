# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ-backed messaging implementations.

Implementations load on demand so importing endpoint constants does not
require the optional ``pyzmq`` package.
"""

from typing import Any

__all__ = ["ZeroMqBroker", "ZeroMqPublisher", "ZeroMqSubscriber"]


def __getattr__(name: str) -> Any:
    if name == "ZeroMqBroker":
        from .broker import ZeroMqBroker

        return ZeroMqBroker
    if name == "ZeroMqPublisher":
        from .publisher import ZeroMqPublisher

        return ZeroMqPublisher
    if name == "ZeroMqSubscriber":
        from .subscriber import ZeroMqSubscriber

        return ZeroMqSubscriber
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
