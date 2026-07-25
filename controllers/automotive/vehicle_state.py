from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class VehicleState:
    """Immutable snapshot of decoded vehicle telemetry.

    Values that were unsupported or unavailable during the latest poll are
    ``None``. Field names include their units where applicable.
    """
    timestamp: datetime

    rpm: float | None = None
    speed_mph: float | None = None

    throttle_pct: float | None = None
    accelerator_pedal_pct: float | None = None
    engine_load_pct: float | None = None

    map_kpa: int | None = None
    baro_kpa: int | None = None
    boost_psi: float | None = None
    maf_gps: float | None = None

    coolant_temp_f: float | None = None
    intake_temp_f: float | None = None

    fuel_level_pct: float | None = None
    control_voltage: float | None = None
