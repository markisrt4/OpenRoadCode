# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Estimate manual-transmission gear from learned engine/road-speed ratios."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

RPM_PER_RAD_S = 60.0 / (2.0 * 3.141592653589793)
MPH_PER_MPS = 2.2369362920544


@dataclass(frozen=True, slots=True)
class GearRatio:
    number: int
    rpm_per_mph: float
    tolerance_fraction: float


class GearEstimator:
    """Map stable RPM/road-speed ratios to a learned forward gear.

    Neutral and reverse cannot be inferred reliably from RPM and road speed
    alone, so this estimator only returns forward gears 1..N or ``None``.
    ``None`` is intentionally used during shifts, clutch slip, low speed, and
    any sample outside the learned ratio envelopes.
    """

    def __init__(
        self,
        ratios: tuple[GearRatio, ...],
        *,
        min_speed_mph: float = 5.0,
        min_rpm: float = 800.0,
        confirmations: int = 3,
    ) -> None:
        if not ratios:
            raise ValueError("at least one learned gear ratio is required")
        if confirmations < 1:
            raise ValueError("confirmations must be at least 1")
        self._ratios = ratios
        self._min_speed_mph = min_speed_mph
        self._min_rpm = min_rpm
        self._confirmations = confirmations
        self._current: int | None = None
        self._candidate: int | None = None
        self._candidate_count = 0

    @classmethod
    def from_toml(
        cls,
        path: str | Path,
        *,
        default_tolerance_fraction: float = 0.08,
        confirmations: int = 3,
    ) -> "GearEstimator":
        profile_path = Path(path).expanduser()
        with profile_path.open("rb") as file:
            data = tomllib.load(file)

        raw_gears = data.get("gear")
        if not isinstance(raw_gears, list) or not raw_gears:
            raise ValueError("gear profile must contain one or more [[gear]] entries")

        ratios: list[GearRatio] = []
        for raw in raw_gears:
            number = int(raw["number"])
            center = float(raw["rpm_per_mph"])
            if number < 1 or center <= 0.0:
                raise ValueError("gear profile contains an invalid gear ratio")

            minimum = float(raw.get("min_rpm_per_mph", center))
            maximum = float(raw.get("max_rpm_per_mph", center))
            learned_spread = max(abs(center - minimum), abs(maximum - center)) / center
            tolerance = max(default_tolerance_fraction, learned_spread * 1.5)
            ratios.append(GearRatio(number, center, tolerance))

        ratios.sort(key=lambda item: item.number)
        return cls(tuple(ratios), confirmations=confirmations)

    @property
    def current_gear(self) -> int | None:
        return self._current

    def estimate(
        self,
        engine_speed_rad_s: float | None,
        vehicle_speed_m_s: float | None,
    ) -> int | None:
        if engine_speed_rad_s is None or vehicle_speed_m_s is None:
            return self._reject()

        rpm = engine_speed_rad_s * RPM_PER_RAD_S
        speed_mph = vehicle_speed_m_s * MPH_PER_MPS
        if rpm < self._min_rpm or speed_mph < self._min_speed_mph:
            return self._reject()

        ratio = rpm / speed_mph
        nearest = min(
            self._ratios,
            key=lambda item: abs(ratio - item.rpm_per_mph) / item.rpm_per_mph,
        )
        error_fraction = abs(ratio - nearest.rpm_per_mph) / nearest.rpm_per_mph
        if error_fraction > nearest.tolerance_fraction:
            return self._reject()

        if nearest.number == self._current:
            self._candidate = None
            self._candidate_count = 0
            return self._current

        if nearest.number != self._candidate:
            self._candidate = nearest.number
            self._candidate_count = 1
        else:
            self._candidate_count += 1

        if self._candidate_count >= self._confirmations:
            self._current = nearest.number
            self._candidate = None
            self._candidate_count = 0
        return self._current

    def _reject(self) -> None:
        # Do not hold a stale gear through a shift or clutch-disengaged period.
        self._current = None
        self._candidate = None
        self._candidate_count = 0
        return None
