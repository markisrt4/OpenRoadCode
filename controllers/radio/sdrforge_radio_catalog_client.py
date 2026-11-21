# SPDX-License-Identifier: MIT
"""Read SDRForge-owned radio profiles and presets over the local REST API.

This client is deliberately read-only. Legacy ORC configuration remains a
fallback until tuning and preset mutation have migrated as well.
"""
from __future__ import annotations

import json
import urllib.request
from urllib.parse import quote
from dataclasses import dataclass

from controllers.radio.sdrforge_readiness import wait_for_sdrforge_ready


@dataclass(frozen=True)
class RemoteRadioPreset:
    id: str
    profile_key: str
    label: str
    frequency_hz: int
    mode_name: str
    bandwidth: int
    step_hz: int
    user_defined: bool


@dataclass(frozen=True)
class RemoteRadioProfile:
    key: str
    label: str
    group: str
    minimum_frequency_hz: int
    maximum_frequency_hz: int
    start_frequency_hz: int
    mode_name: str
    bandwidth: int
    step_hz: int
    presets: tuple[RemoteRadioPreset, ...]


class SdrforgeRadioCatalogClient:
    """Fetch one coherent snapshot from the SDRForge radio catalog."""

    def __init__(self, base_url: str = "http://127.0.0.1:5570", *,
                 timeout: float = 1.5, readiness_timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._readiness_timeout = readiness_timeout

    def _get(self, path: str) -> dict:
        with urllib.request.urlopen(self._base_url + path,
                                    timeout=self._timeout) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("invalid SDRForge radio response")
        return result

    def _mutate(self, method: str, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            self._base_url + path, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method=method,
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("invalid SDRForge preset response")
        return result

    def create_preset(self, *, profile_key: str, label: str,
                      frequency_hz: int, mode: dict | None = None) -> dict:
        payload = {"profile_key": profile_key, "label": label,
                   "frequency_hz": frequency_hz}
        if mode is not None:
            payload["mode"] = mode
        return self._mutate("POST", "/v1/radio/presets", payload)["preset"]

    def delete_preset(self, preset_id: str) -> bool:
        result = self._mutate(
            "DELETE", "/v1/radio/presets/" + quote(preset_id, safe=""),
            {"owner": "default"},
        )
        return result.get("ok") is True

    def profiles(self) -> tuple[RemoteRadioProfile, ...]:
        wait_for_sdrforge_ready(self._base_url, timeout=self._readiness_timeout)
        raw_profiles = self._get("/v1/radio/profiles")["profiles"]
        raw_presets = self._get("/v1/radio/presets")["presets"]
        by_profile: dict[str, list[RemoteRadioPreset]] = {}
        for item in raw_presets:
            mode = item["mode"]
            by_profile.setdefault(str(item["profile_key"]), []).append(
                RemoteRadioPreset(
                    str(item["id"]), str(item["profile_key"]), str(item["label"]),
                    int(item["frequency_hz"]), str(mode["name"]),
                    int(mode["bandwidth_hz"]), int(mode["step_hz"]),
                    item.get("origin") == "user",
                ),
            )
        profiles = []
        for item in raw_profiles:
            mode = item["default_mode"]
            profiles.append(RemoteRadioProfile(
                str(item["key"]), str(item["label"]), str(item["group"]),
                int(item["minimum_frequency_hz"]),
                int(item["maximum_frequency_hz"]),
                int(item["start_frequency_hz"]), str(mode["name"]),
                int(mode["bandwidth_hz"]), int(mode["step_hz"]),
                tuple(by_profile.get(str(item["key"]), ())),
            ))
        return tuple(profiles)
