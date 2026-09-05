# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral hover-help metadata for interactive UI controls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ButtonHelp:
    """Semantic help associated with a button-like UI control.

    Frontends decide how to present this text. Desktop UI may use a hover
    tooltip, while touch-oriented frontends may expose it through another
    discoverability mechanism.
    """

    text: str
    delay_ms: int = 450
