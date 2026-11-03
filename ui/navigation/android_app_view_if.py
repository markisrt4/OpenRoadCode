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
    can_split: bool = True


class AndroidAppViewRequestHandlerIf(Protocol):
    def request_show_android_app(self, app_name: str = 'Android app', package: str = '') -> None:
        """Present the running Android app without taking ownership of its runtime."""
        ...

    def request_toggle_android_app_expanded(self) -> None:
        """Toggle between equal map/app panes and the full-width app view."""
        ...

    def request_set_android_app_visible(self, visible: bool) -> None:
        """Scope optional location forwarding to the embedded app's visibility."""
        ...

    def request_close_android_app(self) -> None:
        """Release this view's retained surface without shutting down the view."""
        ...
