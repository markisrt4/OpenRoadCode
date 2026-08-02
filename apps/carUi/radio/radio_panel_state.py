from __future__ import annotations

from dataclasses import dataclass
from controllers.radio.radio_types import RadioPreset


@dataclass(frozen=True, slots=True)
class RadioPanelState:
    """Immutable state rendered by a Car UI radio panel."""
    receiver_started: bool = False
    frequency_hz: int | None = None
    mode_name: str | None = None
    active_preset: RadioPreset | None = None
    preset_index: int | None = None
    preset_count: int = 0
    signal_strength: float | str | None = None
    snr: float | str | None = None
    rds: str | None = None
