# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable browser frontend for OpenRoadCode."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def create_web_frontend(*args: Any, **kwargs: Any) -> Any:
    """Create the optional Flask-backed web frontend on demand."""
    from frontends.web.web_frontend import create_web_frontend as _create_web_frontend

    factory: Callable[..., Any] = _create_web_frontend
    return factory(*args, **kwargs)


__all__ = ["create_web_frontend"]
