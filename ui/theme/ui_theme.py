# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic, frontend-neutral UI theme values."""

from dataclasses import dataclass
from typing import TypeAlias

Color: TypeAlias = str


@dataclass(frozen=True, slots=True)
class UiTheme:
    """Colors shared by application shells and reusable UI components."""

    background: Color
    surface: Color
    surface_alt: Color
    border: Color
    text: Color
    text_muted: Color
    accent_primary: Color
    accent_success: Color
    accent_warning: Color
    accent_danger: Color
    control_background: Color
    control_active: Color
    control_text: Color
