# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Process-scoped reference to the composition-owned ORC map camera runtime."""

from __future__ import annotations

from apps.orcUi.map_camera_runtime import MapCameraRuntime

_runtime: MapCameraRuntime | None = None


def install_shared_map_camera_runtime(runtime: MapCameraRuntime) -> None:
    """Expose the composition-owned camera runtime to ORC map panels."""
    global _runtime
    if _runtime is not None and _runtime is not runtime:
        raise RuntimeError("ORC map camera runtime is already installed")
    _runtime = runtime


def get_shared_map_camera_runtime() -> MapCameraRuntime:
    """Return the camera runtime installed by the ORC composition root."""
    if _runtime is None:
        raise RuntimeError("ORC map camera runtime has not been installed")
    return _runtime


def clear_shared_map_camera_runtime(runtime: MapCameraRuntime) -> None:
    """Remove a runtime owned and closed by the composition root."""
    global _runtime
    if _runtime is runtime:
        _runtime = None
