# SPDX-License-Identifier: MIT
"""Background NOAA presentation and bounded tuning retries."""
from collections.abc import Callable
from time import sleep
import json
import urllib.request

from controllers.radio.radio_profile_controller import RadioProfileController
from ui.radio.radio_profile_state import RadioProfileState
from ui.radio.rf_radio_if import RadioApplication


def play_weather_radio(radio: RadioProfileController, application: RadioApplication, *,
                       cancelled: Callable[[], bool], native_sdrforge: bool = False) -> RadioProfileState | None:
    profile = radio.catalog.profile("weather_band")
    if not profile.presets:
        raise ValueError("No NOAA weather presets configured")
    if cancelled():
        return None
    application.present()
    for attempt in range(25):
        if cancelled():
            return None
        try:
            if radio.active_profile_key != profile.key:
                radio.select_profile(profile.key)
            station = radio.tune_preset(profile.presets[0])
            if native_sdrforge:
                _ensure_native_receiver_started()
            return station
        except (OSError, RuntimeError, ValueError):
            if attempt == 24:
                raise
            sleep(0.25)
    return None


def _ensure_native_receiver_started() -> None:
    """Start shared SDRForge acquisition only when REST reports it stopped.

    An HTTP 202 acknowledges startup, not successful RF acquisition. The
    existing receiver-status refresh remains responsible for reporting readiness.
    """
    endpoint = "http://127.0.0.1:5570/v1/receiver"
    with urllib.request.urlopen(endpoint, timeout=2.0) as response:
        status = json.load(response)
    if status.get("running") or status.get("starting"):
        return
    with urllib.request.urlopen(
        urllib.request.Request(endpoint + "/start", data=b"", method="POST"),
        timeout=6.0,
    ) as response:
        if response.status not in (200, 202):
            raise RuntimeError(f"SDRForge receiver start returned HTTP {response.status}")
