# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from dataclasses import dataclass

from ui.icon import IconId


@dataclass(frozen=True, slots=True)
class MenuTile:
    """Describe one selectable navigation tile."""

    key: str
    title: str
    subtitle: str
    detail: str
    icon: IconId | None = None
