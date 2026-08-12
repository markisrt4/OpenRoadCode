# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""External application launcher interfaces and implementations."""

from apps.launchers.adsb_launcher import ADSBLauncher
from apps.launchers.app_launcher_if import (
    AppLauncherIf,
    StatusCallback,
)
from apps.launchers.app_launcher_stub import AppLauncherStub
from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.sdrpp_launcher import (
    SDRPPLauncher,
    SDRPPProfile,
)
from apps.launchers.streamlit_launcher import StreamlitLauncher
from apps.launchers.weather_dash_launcher import WeatherDashLauncher

__all__ = [
    "ADSBLauncher",
    "AppLauncherIf",
    "AppLauncherStub",
    "BrowserKioskLauncher",
    "SDRPPLauncher",
    "SDRPPProfile",
    "StatusCallback",
    "StreamlitLauncher",
    "WeatherDashLauncher",
]
