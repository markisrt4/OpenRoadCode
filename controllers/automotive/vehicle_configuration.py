# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from enum import Enum


class EngineInductionType(str, Enum):
    UNKNOWN = "unknown"
    NATURALLY_ASPIRATED = "naturally_aspirated"
    TURBOCHARGED = "turbocharged"
    SUPERCHARGED = "supercharged"

    @property
    def display_name(self) -> str:
        return {
            EngineInductionType.UNKNOWN: "Unknown / Not configured",
            EngineInductionType.NATURALLY_ASPIRATED: "Naturally Aspirated",
            EngineInductionType.TURBOCHARGED: "Turbocharged",
            EngineInductionType.SUPERCHARGED: "Supercharged",
        }[self]

    @property
    def is_forced_induction(self) -> bool:
        return self in {
            EngineInductionType.TURBOCHARGED,
            EngineInductionType.SUPERCHARGED,
        }


@dataclass(frozen=True, slots=True)
class VehicleConfiguration:
    induction: EngineInductionType = EngineInductionType.UNKNOWN
