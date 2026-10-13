# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Select camera hardware at composition, keeping platform access out of widgets."""

from collections.abc import Mapping
import os

from hardware_io.camera.android_bridge_camera import AndroidBridgeCamera
from hardware_io.camera.camera_controls_if import CameraControlsIf
from hardware_io.camera.camera_if import CameraIf
from hardware_io.camera.software_camera_controls import SoftwareCameraControls
from hardware_io.camera.v4l2_camera import V4L2Camera
from hardware_io.camera.v4l2_camera_controls import V4L2CameraProfileController


def create_vision_camera(environment: Mapping[str, str] | None = None
                         ) -> tuple[CameraIf, CameraControlsIf, str]:
    """Use Android streaming on Termux and V4L2 on desktop/Linux by default."""
    environment = os.environ if environment is None else environment
    termux = environment.get("PREFIX", "").startswith("/data/data/com.termux/files/usr")
    source = environment.get("OPENROADCODE_VISION_CAMERA_SOURCE", "android_bridge" if termux else "v4l2")
    if source == "android_bridge":
        base_url = environment.get("OPENROADCODE_VISION_BRIDGE_URL", "http://127.0.0.1:8767")
        return AndroidBridgeCamera(base_url), SoftwareCameraControls(), "Android Bridge camera"
    if source == "v4l2":
        device = environment.get("OPENROADCODE_VISION_CAMERA_DEVICE", "/dev/video0")
        return (V4L2Camera(device, width=1920, height=1080, fps=30.0, pixel_format="MJPG"),
                V4L2CameraProfileController(device), device)
    raise ValueError("OPENROADCODE_VISION_CAMERA_SOURCE must be android_bridge or v4l2")
