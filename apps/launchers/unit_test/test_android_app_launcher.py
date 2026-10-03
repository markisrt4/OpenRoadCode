# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock, patch

import pytest

from apps.launchers.android_app_launcher import (
    AndroidAppLauncher,
    AndroidAppLauncherError,
)
from apps.launchers.android_bridge_launcher import AndroidBridgeLauncherError
from apps.launchers.waydroid_launcher import AndroidApp, WaydroidLauncherError
from apps.launchers.desktop_browser_launcher import DesktopBrowserLauncherError


@patch("apps.launchers.android_app_launcher.os.path.exists", return_value=False)
def test_linux_launches_package_through_waydroid(_exists) -> None:
    waydroid = Mock()
    waydroid.list_apps.return_value = (AndroidApp("Panera", "com.panera.bread"),)
    launcher = AndroidAppLauncher(waydroid=waydroid)

    destination = launcher.open_package_or_uri(
        "com.panera.bread",
        "https://www.panerabread.com/en-us/start-an-order.html",
    )

    waydroid.launch_app.assert_called_once_with("com.panera.bread")
    assert destination == "Waydroid"


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
def test_linux_without_package_uses_default_browser(_exists) -> None:
    browser, waydroid = Mock(), Mock()
    launcher = AndroidAppLauncher(waydroid=waydroid, browser=browser)
    assert launcher.open_package_or_uri(None, "https://example.com") == "browser"
    launcher.open_uri("https://example.com/about")
    assert browser.open_uri.call_count == 2
    waydroid.list_apps.assert_not_called()


@pytest.mark.parametrize("failure", ["missing_package", "unavailable", "launch_failed"])
@patch("apps.launchers.android_app_launcher.os.path.exists", return_value=False)
def test_linux_falls_back_when_android_app_cannot_launch(_exists, failure) -> None:
    browser, waydroid = Mock(), Mock()
    waydroid.list_apps.return_value = ()
    if failure == "unavailable":
        waydroid.list_apps.side_effect = WaydroidLauncherError("not installed")
    elif failure == "launch_failed":
        waydroid.list_apps.return_value = (AndroidApp("Panera", "com.panera.bread"),)
        waydroid.launch_app.side_effect = WaydroidLauncherError("session unavailable")
    launcher = AndroidAppLauncher(waydroid=waydroid, browser=browser)
    assert launcher.open_package_or_uri("com.panera.bread", "https://example.com") == "browser"
    browser.open_uri.assert_called_once_with("https://example.com")


@patch("apps.launchers.android_app_launcher.os.path.exists", return_value=False)
def test_browser_failure_is_reported(_exists) -> None:
    browser = Mock()
    browser.open_uri.side_effect = DesktopBrowserLauncherError("no default browser")
    with pytest.raises(AndroidAppLauncherError, match="no default browser"):
        AndroidAppLauncher(browser=browser).open_uri("https://example.com")


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
