# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock, patch

import pytest

from apps.launchers.android_app_launcher import (
    AndroidAppLauncher,
    AndroidAppLauncherError,
)
from apps.launchers.android_bridge_launcher import AndroidBridgeLauncherError


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
def test_android_delegates_to_bridge_launcher(_exists) -> None:
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


@patch("apps.launchers.android_app_launcher.os.path.exists", return_value=True)
@patch("apps.launchers.android_app_launcher.AndroidBridgeLauncher")
def test_android_creates_default_bridge_client(client_class, _exists) -> None:
    client_class.return_value.open_package_or_uri.return_value = "app"
    launcher = AndroidAppLauncher()

    assert launcher.open_package_or_uri("com.panera.bread", "https://example.com") == "app"
    client_class.return_value.open_package_or_uri.assert_called_once_with(
        "com.panera.bread", "https://example.com"
    )
    launcher.open_uri("https://example.com")
    client_class.return_value.open_uri.assert_called_once_with("https://example.com")


@pytest.mark.parametrize("operation", ["open_uri", "open_package_or_uri"])
@patch("apps.launchers.android_app_launcher.os.path.exists", return_value=True)
def test_android_bridge_errors_are_reported_as_launcher_errors(_exists, operation) -> None:
    native = Mock()
    error = AndroidBridgeLauncherError("bridge unavailable")
    getattr(native, operation).side_effect = error
    launcher = AndroidAppLauncher(native=native)
    args = ("https://example.com",) if operation == "open_uri" else (
        "com.panera.bread", "https://example.com"
    )

    with pytest.raises(AndroidAppLauncherError, match="bridge unavailable") as raised:
        getattr(launcher, operation)(*args)

    assert raised.value.__cause__ is error
