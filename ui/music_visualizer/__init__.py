# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral music visualizer contracts."""

from .music_visualizer_request_handler_if import MusicVisualizerRequestHandlerIf
from .music_visualizer_types import KickMode, MusicVisualizationMode

__all__ = [
    "KickMode",
    "MusicVisualizationMode",
    "MusicVisualizerRequestHandlerIf",
]
