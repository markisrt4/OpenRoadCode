# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility exports; shared contracts live in the independent UI package."""

from ui.automotive.vehicle_configuration import (
    EngineInductionType,
    VehicleConfiguration,
)

__all__ = ['EngineInductionType', 'VehicleConfiguration']
