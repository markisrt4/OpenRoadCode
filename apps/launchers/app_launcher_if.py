# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility exports; shared contracts live in the independent UI package."""

from ui.system.app_launcher_if import (
    StatusCallback,
    AppLauncherIf,
    HideableAppLauncherIf,
    WindowedAppLauncherIf,
    PreloadableAppLauncherIf,
    BrowserDashboardLauncherIf,
)

__all__ = ['StatusCallback', 'AppLauncherIf', 'HideableAppLauncherIf', 'WindowedAppLauncherIf', 'PreloadableAppLauncherIf', 'BrowserDashboardLauncherIf']
