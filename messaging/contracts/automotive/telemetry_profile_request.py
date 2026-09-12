# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from controllers.automotive.automotive_telemetry_profile import AutomotiveTelemetryProfile


@dataclass(frozen=True, slots=True)
class AutomotiveTelemetryProfileRequest:
    profile: AutomotiveTelemetryProfile
    source: str


def encode_automotive_telemetry_profile_request(
    profile: AutomotiveTelemetryProfile,
    *,
    source: str,
) -> dict[str, Any]:
    if not source.strip():
        raise ValueError("source must not be empty")
    return {"version": 1, "source": source, "profile": profile.value}


def decode_automotive_telemetry_profile_request(
    payload: Mapping[str, Any],
) -> AutomotiveTelemetryProfileRequest:
    if set(payload) != {"version", "source", "profile"}:
        raise ValueError("telemetry profile request schema mismatch")
    if payload["version"] != 1:
        raise ValueError(f"unsupported telemetry profile request version: {payload['version']}")
    source = payload["source"]
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string")
    try:
        profile = AutomotiveTelemetryProfile(payload["profile"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"unknown automotive telemetry profile: {payload['profile']}") from exc
    return AutomotiveTelemetryProfileRequest(profile=profile, source=source)
