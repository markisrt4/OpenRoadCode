# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""External application launcher interfaces and implementations."""

from importlib import import_module
from typing import Any

from apps.launchers.app_launcher_if import AppLauncherIf, StatusCallback
from apps.launchers.app_launcher_stub import AppLauncherStub

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

_LAZY_EXPORTS = {
    "ADSBLauncher": ("apps.launchers.adsb_launcher", "ADSBLauncher"),
    "BrowserKioskLauncher": ("apps.launchers.browser_launcher", "BrowserKioskLauncher"),
    "SDRPPLauncher": ("apps.launchers.sdrpp_launcher", "SDRPPLauncher"),
    "SDRPPProfile": ("apps.launchers.sdrpp_launcher", "SDRPPProfile"),
    "StreamlitLauncher": ("apps.launchers.streamlit_launcher", "StreamlitLauncher"),
    "WeatherDashLauncher": ("apps.launchers.weather_dash_launcher", "WeatherDashLauncher"),
}


def __getattr__(name: str) -> Any:
    """Load concrete launchers only when explicitly requested."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
