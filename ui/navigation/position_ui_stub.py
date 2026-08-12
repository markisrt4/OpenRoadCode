# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op position UI implementation."""

from collections.abc import Sequence

from ui.navigation.position_ui_if import PositionFix, PositionUiIf, SatelliteInfo


class PositionUiStub(PositionUiIf):
    """Ignore position and satellite display updates."""

    def set_position(self, position_fix: PositionFix | None) -> None:
        pass

    def set_satellites(self, satellites: Sequence[SatelliteInfo]) -> None:
        pass
