# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from enum import Enum


class FuelControlMode(str, Enum):
    OPEN_LOOP_WARMUP = "open_loop_warmup"
    CLOSED_LOOP = "closed_loop"
    OPEN_LOOP_LOAD_OR_DECEL = "open_loop_load_or_decel"
    OPEN_LOOP_FAULT = "open_loop_fault"
    CLOSED_LOOP_FAULT = "closed_loop_fault"
    UNKNOWN = "unknown"


class EngineOperatingMode(str, Enum):
    OFF = "off"
    IDLE = "idle"
    CRUISE = "cruise"
    ACCELERATION = "acceleration"
    HIGH_LOAD = "high_load"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class EngineAnalysis:
    """ORC-derived interpretation of one vehicle telemetry snapshot."""

    operating_mode: EngineOperatingMode
    fuel_control_mode: FuelControlMode

    engine_running: bool | None
    warmed_up: bool | None
    enrichment_active: bool | None
    high_load: bool | None
    forced_induction_active: bool | None

    fuel_trim_total: float | None
    mixture_tracking_error: float | None
    throttle_tracking_error: float | None
