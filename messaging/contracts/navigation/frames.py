# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Stable coordinate-frame identifiers used by navigation contracts."""

ANDROID_DEVICE_FRAME = "android_device"
VEHICLE_FRAME = "vehicle"
WORLD_ENU_FRAME = "world_enu"
WORLD_NED_FRAME = "world_ned"

KNOWN_FRAME_IDS = frozenset({
    ANDROID_DEVICE_FRAME,
    VEHICLE_FRAME,
    WORLD_ENU_FRAME,
    WORLD_NED_FRAME,
})


def validate_frame_id(frame_id: object) -> str:
    """Validate and return a known navigation coordinate-frame identifier."""
    if not isinstance(frame_id, str) or not frame_id:
        raise ValueError("frame_id must be a non-empty string")
    if frame_id not in KNOWN_FRAME_IDS:
        supported = ", ".join(sorted(KNOWN_FRAME_IDS))
        raise ValueError(f"unsupported frame_id '{frame_id}'; expected one of: {supported}")
    return frame_id
