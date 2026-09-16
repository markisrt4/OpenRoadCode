# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-independent application settings state."""

from __future__ import annotations

from dataclasses import dataclass

from common.units import UnitSystem


@dataclass(frozen=True, slots=True)
class SettingsState:
    """Application-wide presentation preferences."""

    unit_system: UnitSystem = UnitSystem.IMPERIAL
