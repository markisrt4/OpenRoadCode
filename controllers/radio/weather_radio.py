# SPDX-License-Identifier: MIT
"""Background NOAA presentation and bounded tuning retries."""
from collections.abc import Callable
from time import sleep

from controllers.radio.radio_profile_controller import RadioProfileController
from ui.radio.radio_profile_state import RadioProfileState
from ui.radio.rf_radio_if import RadioApplication


def play_weather_radio(radio: RadioProfileController, application: RadioApplication, *,
                       cancelled: Callable[[], bool]) -> RadioProfileState | None:
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
            return radio.tune_preset(profile.presets[0])
        except (OSError, RuntimeError, ValueError):
            if attempt == 24:
                raise
            sleep(0.25)
    return None
