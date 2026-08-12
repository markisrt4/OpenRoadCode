# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op translation UI implementation."""

from ui.navigation.translation_ui_if import TranslationUiIf


class TranslationUiStub(TranslationUiIf):
    """Ignore translational-motion display updates."""

    def set_rate_of_climb(self, rate_mps: float | None) -> None:
        pass

    def set_accel_x(self, acceleration_x_mps2: float | None) -> None:
        pass

    def set_accel_y(self, acceleration_y_mps2: float | None) -> None:
        pass

    def set_accel_z(self, acceleration_z_mps2: float | None) -> None:
        pass

    def set_accel_total(self, acceleration_magnitude_mps2: float | None) -> None:
        pass
