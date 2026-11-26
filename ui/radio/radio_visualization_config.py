# SPDX-License-Identifier: MIT
"""Frontend-neutral configuration and backend selection for radio visualization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


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


class RadioVisualizationSettingsIf(Protocol):
    """Read and update persisted RF display preferences."""

    def load(self, defaults: RadioVisualizationConfig | None = None) -> RadioVisualizationConfig:
        ...

    def save(self, config: RadioVisualizationConfig) -> None:
        ...
