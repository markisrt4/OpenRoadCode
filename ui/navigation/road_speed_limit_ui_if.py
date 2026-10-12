# SPDX-License-Identifier: MIT
"""Toolkit-independent mapped road-limit presentation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class RoadSpeedLimitState:
    limit_mps: float | None = None
    road_name: str = ""

    def __post_init__(self) -> None:
        if self.limit_mps is not None and (isinstance(self.limit_mps, bool) or not math.isfinite(self.limit_mps) or self.limit_mps <= 0):
            raise ValueError("Road limit must be finite and positive")


class RoadSpeedLimitUiIf(ABC):
    @abstractmethod
    def set_road_speed_limit(self, state: RoadSpeedLimitState) -> None:
        """! @brief Replace the mapped road-limit snapshot.
        @param state SI limit, or an unknown snapshot when no usable match exists.
        """
