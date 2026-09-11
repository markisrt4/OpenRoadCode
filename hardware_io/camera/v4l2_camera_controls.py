# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""V4L2 hardware-control profiles for road-camera capture."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum


class V4L2CameraProfile(str, Enum):
    """Named hardware profiles used by the road-camera pipeline."""

    DAY = "day"
    LOW_LIGHT = "low_light"


@dataclass(frozen=True, slots=True)
class V4L2ControlProfile:
    """Concrete V4L2 control values for one camera profile."""

    auto_exposure: int
    exposure_time_absolute: int | None
    gain: int
    gamma: int
    backlight_compensation: int
    power_line_frequency: int = 2


DAY_PROFILE = V4L2ControlProfile(
    auto_exposure=0,
    exposure_time_absolute=None,
    gain=1,
    gamma=200,
    backlight_compensation=0,
    power_line_frequency=2,
)

LOW_LIGHT_PROFILE = V4L2ControlProfile(
    auto_exposure=2,
    exposure_time_absolute=250,
    gain=10,
    gamma=220,
    backlight_compensation=1,
    power_line_frequency=2,
)


class V4L2CameraProfileController:
    """Apply repeatable hardware profiles through v4l2-ctl.

    The profile values target the USB camera validated for OpenRoadCode. The
    exposure value uses the UVC/V4L2 absolute-exposure unit reported by the
    device; 250 is roughly 25 ms, which preserves useful motion detail while
    allowing more light than the camera's 15.6 ms default.
    """

    def __init__(self, device: str = "/dev/video0") -> None:
        self._device = device
        self._current_profile: V4L2CameraProfile | None = None

    @property
    def current_profile(self) -> V4L2CameraProfile | None:
        return self._current_profile

    def apply(self, profile: V4L2CameraProfile) -> None:
        selected = V4L2CameraProfile(profile)
        if selected is self._current_profile:
            return

        values = DAY_PROFILE if selected is V4L2CameraProfile.DAY else LOW_LIGHT_PROFILE
        self._set_control("power_line_frequency", values.power_line_frequency)

        # Exposure mode must change before exposure_time_absolute becomes active.
        self._set_control("auto_exposure", values.auto_exposure)
        if values.exposure_time_absolute is not None:
            self._set_control("exposure_time_absolute", values.exposure_time_absolute)

        self._set_control("gain", values.gain)
        self._set_control("gamma", values.gamma)
        self._set_control("backlight_compensation", values.backlight_compensation)
        self._current_profile = selected

    def restore_day_defaults(self) -> None:
        """Return the camera to the conservative daytime hardware profile."""
        self.apply(V4L2CameraProfile.DAY)

    def _set_control(self, name: str, value: int) -> None:
        try:
            completed = subprocess.run(
                [
                    "v4l2-ctl",
                    "-d",
                    self._device,
                    "--set-ctrl",
                    f"{name}={value}",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("v4l2-ctl is required for camera hardware controls") from exc

        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Unable to set {name}={value}: {detail}")
