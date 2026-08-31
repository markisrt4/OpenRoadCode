# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Process-lifetime map camera runtime shared by ORC UI map panels."""

from __future__ import annotations

import math

from apps.orcUi.map_camera_runtime import MapCameraRuntime

_runtime: MapCameraRuntime | None = None
_started = False


def get_shared_map_camera_runtime() -> MapCameraRuntime:
    """Return the process-lifetime camera runtime, starting it once."""
    global _runtime, _started
    if _runtime is None:
        _runtime = MapCameraRuntime(
            zoom_level=16.5,
            pitch_rad=math.radians(45.0),
            follow_enabled=True,
        )
    if not _started:
        _runtime.start()
        _started = True
    return _runtime
