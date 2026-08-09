from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RadioPanelTileConfig:
    """Define the text displayed on a radio-panel action tile."""
    label: str
    subtitle: str
    detail: str


@dataclass(frozen=True)
class RadioPanelConfig:
    """Configure labels, tuning defaults, and layout for a radio panel."""
    key: str
    title: str
    launch_tile: RadioPanelTileConfig
    radio_toggle_tile: RadioPanelTileConfig
    default_step_hz: int
    default_mode_name: str = "Radio"
    preset_columns: int = 2
