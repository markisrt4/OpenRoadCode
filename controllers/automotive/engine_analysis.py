# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility exports; shared contracts live in the independent UI package."""

from ui.automotive.engine_analysis import (
    FuelControlMode,
    EngineOperatingMode,
    MixtureMode,
    TrackingQuality,
    FuelCorrectionStatus,
    EngineLoadLevel,
    EngineAnalysis,
)

__all__ = ['FuelControlMode', 'EngineOperatingMode', 'MixtureMode', 'TrackingQuality', 'FuelCorrectionStatus', 'EngineLoadLevel', 'EngineAnalysis']
