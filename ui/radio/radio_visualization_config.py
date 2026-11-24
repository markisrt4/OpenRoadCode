# SPDX-License-Identifier: MIT
"""Frontend-neutral configuration and backend selection for radio visualization."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from enum import Enum


class RadioRenderer(str, Enum):
    AUTO = "auto"
    OPENGL = "opengl"
    TK = "tk"


@dataclass(frozen=True, slots=True)
class RadioVisualizationConfig:
    renderer: RadioRenderer = RadioRenderer.AUTO
    waterfall_rows: int = 180
    max_fps: int = 10
    palette: str = "classic"

    def __post_init__(self) -> None:
        if not 30 <= self.waterfall_rows <= 1024:
            raise ValueError("waterfall_rows must be between 30 and 1024")
        if not 1 <= self.max_fps <= 60:
            raise ValueError("max_fps must be between 1 and 60")
        if self.palette not in {"classic", "grayscale"}:
            raise ValueError("unsupported waterfall palette")


def select_renderer(config: RadioVisualizationConfig, *, opengl_available: bool) -> RadioRenderer:
    """Auto falls back; an explicit OpenGL request never silently falls back."""
    if config.renderer is RadioRenderer.TK:
        return RadioRenderer.TK
    if config.renderer is RadioRenderer.OPENGL:
        if not opengl_available:
            raise RuntimeError("OpenGL radio renderer is unavailable on this display")
        return RadioRenderer.OPENGL
    return RadioRenderer.OPENGL if opengl_available else RadioRenderer.TK


RF_SETTINGS_PATH = Path.home() / ".config" / "openroadcode" / "rf_visualization.json"


def load_rf_visualization_settings() -> dict[str, object]:
    """Load optional user overrides without preventing the radio from starting."""
    try:
        value = json.loads(RF_SETTINGS_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_rf_visualization_settings(values: dict[str, object]) -> None:
    """Persist advanced RF display preferences for the next radio view."""
    RF_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RF_SETTINGS_PATH.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
