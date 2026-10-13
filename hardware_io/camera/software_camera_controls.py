# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Profile bookkeeping for sources whose exposure is managed outside ORC."""

from hardware_io.camera.camera_controls_if import CameraControlsIf, CameraProfile


class SoftwareCameraControls(CameraControlsIf):
    """Keep software DAY/LOW_LIGHT processing without issuing hardware controls.

    Android Camera2 owns exposure. The existing CameraFrameProcessor performs
    ORC's day/low-light enhancement; this adapter does not claim to alter exposure.
    """

    def __init__(self) -> None:
        self._profile: CameraProfile | None = None

    @property
    def current_profile(self) -> CameraProfile | None:
        return self._profile

    def apply(self, profile: CameraProfile) -> None:
        self._profile = CameraProfile(profile)

    def invalidate(self) -> None:
        self._profile = None

    def restore_day_defaults(self) -> None:
        self.apply(CameraProfile.DAY)
