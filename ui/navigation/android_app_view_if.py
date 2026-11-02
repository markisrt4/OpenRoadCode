# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Semantic presentation request, callable from app-launch workers."""
from typing import Protocol
from dataclasses import dataclass


@dataclass(frozen=True)
class AndroidAppViewState:
    """Identity and presentation of the app; no Android transport details."""
    app_name: str = 'Android app'
    package: str = ''
    expanded: bool = False
    trim_android_frame: bool = False


class AndroidAppViewRequestHandlerIf(Protocol):
    def request_show_android_app(self, app_name: str = 'Android app', package: str = '') -> None:
        """Present the running Android app without taking ownership of its runtime."""
        ...

    def request_toggle_android_app_expanded(self) -> None:
        """Toggle between equal map/app panes and the full-width app view."""
        ...

    def request_toggle_android_frame_trim(self) -> None:
        """Toggle visual clipping of system chrome in the hosted Android view."""
        ...
