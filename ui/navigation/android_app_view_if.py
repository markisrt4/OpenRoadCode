# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Semantic presentation request, callable from app-launch workers."""
from typing import Protocol


class AndroidAppViewRequestHandlerIf(Protocol):
    def request_show_android_app(self) -> None:
        """Present the running Android app without taking ownership of its runtime."""
        ...
