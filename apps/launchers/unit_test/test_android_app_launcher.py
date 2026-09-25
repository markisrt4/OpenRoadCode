# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock, patch

import pytest

from apps.launchers.android_app_launcher import (
    AndroidAppLauncher,
    AndroidAppLauncherError,
)


@patch("apps.launchers.android_app_launcher.os.path.exists", return_value=False)
def test_linux_launches_package_through_waydroid(_exists) -> None:
    waydroid = Mock()
    launcher = AndroidAppLauncher(waydroid=waydroid)

    destination = launcher.open_package_or_uri(
        "com.panera.bread",
        "https://www.panerabread.com/en-us/start-an-order.html",
    )

    waydroid.launch_app.assert_called_once_with("com.panera.bread")
    assert destination == "waydroid"


@patch("apps.launchers.android_app_launcher.os.path.exists", return_value=True)
def test_android_delegates_to_native_intent_launcher(_exists) -> None:
    native = Mock()
    native.open_package_or_uri.return_value = "app"
    launcher = AndroidAppLauncher(native=native)

    destination = launcher.open_package_or_uri(
        "com.panera.bread",
        "https://www.panerabread.com/en-us/start-an-order.html",
    )

    assert destination == "app"
    native.open_package_or_uri.assert_called_once()


@patch("apps.launchers.android_app_launcher.os.path.exists", return_value=False)
def test_linux_without_package_reports_clear_error(_exists) -> None:
    launcher = AndroidAppLauncher(waydroid=Mock())

    with pytest.raises(AndroidAppLauncherError):
        launcher.open_package_or_uri(None, "https://example.com")
