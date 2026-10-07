# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""V4L2 hardware-control profiles for road-camera capture."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from enum import Enum

from hardware_io.camera.camera_controls_if import CameraControlsIf, CameraProfile


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
    # This camera reports exposure_time_absolute as inactive and rejects writes
    # while streaming, so keep its supported auto-exposure mode and improve
    # low-light response with controls the device actually accepts.
    auto_exposure=0,
    exposure_time_absolute=None,
    gain=10,
    gamma=220,
    backlight_compensation=1,
    power_line_frequency=2,
)


class V4L2CameraProfileController(CameraControlsIf):
    """Apply repeatable hardware profiles through v4l2-ctl.

    The profile values target the USB camera validated for OpenRoadCode.
    Although the device advertises exposure_time_absolute, it reports that
    control inactive and rejects writes while streaming. Low-light mode
    therefore leaves exposure automatic and uses supported gain, gamma, and
    backlight controls instead.
    """

    def __init__(self, device: str = "/dev/video0") -> None:
        self._device = device
        self._current_profile: V4L2CameraProfile | None = None
        self._supported_profiles: frozenset[CameraProfile] = frozenset()

    @property
    def current_profile(self) -> CameraProfile | None:
        if self._current_profile is None:
            return None
        return CameraProfile(self._current_profile.value)

    def probe_supported_profiles(self) -> frozenset[CameraProfile]:
        """Return profiles whose controls and exact values the device advertises."""
        try:
            completed = subprocess.run(
                ["v4l2-ctl", "-d", self._device, "--list-ctrls-menus"],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            self._supported_profiles = frozenset()
            return self._supported_profiles

        if completed.returncode != 0:
            self._supported_profiles = frozenset()
            return self._supported_profiles

        controls = self._parse_controls(completed.stdout)
        supported = {
            CameraProfile(profile.value)
            for profile, values in (
                (V4L2CameraProfile.DAY, DAY_PROFILE),
                (V4L2CameraProfile.LOW_LIGHT, LOW_LIGHT_PROFILE),
            )
            if self._profile_supported(values, controls)
        }
        self._supported_profiles = frozenset(supported)
        return self._supported_profiles

    def apply(self, profile: CameraProfile) -> None:
        selected = V4L2CameraProfile(CameraProfile(profile).value)
        if selected is self._current_profile:
            return
        if CameraProfile(selected.value) not in self._supported_profiles:
            raise RuntimeError(f"Camera does not support the {selected.value} profile")

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

    def invalidate(self) -> None:
        """Forget cached profile state after the device is reopened or reset."""
        self._current_profile = None

    def restore_day_defaults(self) -> None:
        """Return the camera to the conservative daytime hardware profile."""
        if CameraProfile.DAY in self._supported_profiles:
            self.apply(CameraProfile.DAY)

    @staticmethod
    def _profile_supported(
        profile: V4L2ControlProfile,
        controls: dict[str, tuple[int, int, frozenset[int] | None]],
    ) -> bool:
        values = {
            "auto_exposure": profile.auto_exposure,
            "gain": profile.gain,
            "gamma": profile.gamma,
            "backlight_compensation": profile.backlight_compensation,
            "power_line_frequency": profile.power_line_frequency,
        }
        if profile.exposure_time_absolute is not None:
            values["exposure_time_absolute"] = profile.exposure_time_absolute
        for name, value in values.items():
            control = controls.get(name)
            if control is None:
                return False
            minimum, maximum, menu_values = control
            if not minimum <= value <= maximum:
                return False
            if menu_values is not None and value not in menu_values:
                return False
        return True

    @staticmethod
    def _parse_controls(
        output: str,
    ) -> dict[str, tuple[int, int, frozenset[int] | None]]:
        controls: dict[str, tuple[int, int, frozenset[int] | None]] = {}
        current_name: str | None = None
        menu_values: dict[str, set[int]] = {}
        for line in output.splitlines():
            match = re.match(
                r"^\s*([a-zA-Z0-9_]+)\s+0x[0-9a-fA-F]+\s+\(([^)]+)\)"
                r"\s*:\s*min=(-?\d+)\s+max=(-?\d+)",
                line,
            )
            if match:
                current_name = match.group(1)
                kind = match.group(2)
                controls[current_name] = (
                    int(match.group(3)),
                    int(match.group(4)),
                    frozenset() if kind in {"menu", "intmenu", "integer menu"} else None,
                )
                if kind in {"menu", "intmenu", "integer menu"}:
                    menu_values[current_name] = set()
                continue
            menu_match = re.match(r"^\s+(-?\d+):", line)
            if current_name in menu_values and menu_match:
                menu_values[current_name].add(int(menu_match.group(1)))
        for name, values in menu_values.items():
            minimum, maximum, _ = controls[name]
            controls[name] = (minimum, maximum, frozenset(values))
        return controls

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
