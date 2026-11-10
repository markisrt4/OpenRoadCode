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


@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=True)
def test_termux_ordering_prefers_the_embedded_business_view_when_available(_exists):
    native, view, installed = Mock(), Mock(), Mock()
    installed.launch_installed_app.return_value = 'Panera Bread'
    launcher = AndroidAppLauncher(native=native, app_view=view, installed_apps=installed)
    assert launcher.open_package_or_uri('com.panera.bread', 'https://www.panerabread.com') == 'embedded Android app'
    installed.launch_installed_app.assert_called_once_with('com.panera.bread')
    view.request_show_android_app.assert_called_once_with('Panera Bread', 'com.panera.bread')
    native.open_package_or_uri.assert_not_called()


@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=True)
def test_termux_ordering_keeps_bridge_fallback_when_app_or_adb_is_unavailable(_exists):
    native, view, installed = Mock(), Mock(), Mock()
    installed.launch_installed_app.return_value = None
    native.open_package_or_uri.return_value = 'Android'
    launcher = AndroidAppLauncher(native=native, app_view=view, installed_apps=installed)
    assert launcher.open_package_or_uri('com.panera.bread', 'https://www.panerabread.com') == 'Android'
    native.open_package_or_uri.assert_called_once_with('com.panera.bread', 'https://www.panerabread.com')
    view.request_show_android_app.assert_not_called()


@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=False)
def test_missing_business_app_opens_google_play_inside_waydroid_without_installing(_exists):
    waydroid, browser, view = Mock(), Mock(), Mock()
    waydroid.list_apps.return_value = (AndroidApp('Play Store', 'com.android.vending'),)
    launcher = AndroidAppLauncher(waydroid=waydroid, browser=browser, app_view=view)
    result = launcher.open_android_app('com.panera.bread')
    waydroid.launch_uri.assert_called_once_with('market://details?id=com.panera.bread')
    waydroid.launch_app.assert_not_called()
    view.request_show_android_app.assert_called_once_with('Google Play — install app', 'com.android.vending')
    browser.open_uri.assert_not_called()
    assert 'review and install' in result


@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=False)
def test_installed_business_app_resumes_normal_embedding_without_opening_store(_exists):
    waydroid, view = Mock(), Mock()
    waydroid.list_apps.return_value = (AndroidApp('Panera', 'com.panera.bread'),)
    launcher = AndroidAppLauncher(waydroid=waydroid, app_view=view)
    assert launcher.open_android_app('com.panera.bread') == 'Panera'
    waydroid.launch_app.assert_called_once_with('com.panera.bread')
    view.request_show_android_app.assert_called_once_with('Panera', 'com.panera.bread')
    waydroid.launch_uri.assert_not_called()


@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=False)
def test_missing_play_store_is_an_explicit_error_not_a_linux_browser_handoff(_exists):
    waydroid, browser = Mock(), Mock()
    waydroid.list_apps.return_value = ()
    launcher = AndroidAppLauncher(waydroid=waydroid, browser=browser)
    with pytest.raises(AndroidAppLauncherError, match='Enable Google Play'):
        launcher.open_android_app('com.panera.bread')
    browser.open_uri.assert_not_called()


@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=True)
def test_termux_business_app_handoff_uses_existing_app_first_bridge_and_official_store_listing(_exists):
    native = Mock()
    launcher = AndroidAppLauncher(native=native)
    launcher.open_android_app('com.panera.bread')
    native.open_package_or_uri.assert_called_once_with('com.panera.bread', 'https://play.google.com/store/apps/details?id=com.panera.bread')


def test_install_action_rejects_invalid_package_before_any_platform_handoff():
    launcher = AndroidAppLauncher(native=Mock(), waydroid=Mock())
    with pytest.raises(ValueError, match='Invalid Android package'):
        launcher.open_android_app('com.example.app --bad-argument')


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


@patch("apps.launchers.android_app_launcher.os.path.exists", return_value=False)
def test_panel_requested_only_after_successful_android_launch(_exists):
    waydroid, browser, view = Mock(), Mock(), Mock()
    waydroid.list_apps.return_value = (AndroidApp('Panera', 'com.panera.bread'),)
    launcher = AndroidAppLauncher(waydroid=waydroid, browser=browser, app_view=view)
    launcher.open_package_or_uri('com.panera.bread', 'https://example.com')
    view.request_show_android_app.assert_called_once_with('Panera', 'com.panera.bread')
    view.reset_mock()
    waydroid.launch_app.side_effect = WaydroidLauncherError('stopped')
    assert launcher.open_package_or_uri('com.panera.bread', 'https://example.com') == 'browser'
    view.request_show_android_app.assert_not_called()


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


@pytest.mark.parametrize('code,stdout,stderr,expected', [
    (0, 'package:/data/app/business.apk\n', '', True),
    (1, '', '', False),
    (1, '', 'adb: device unauthorized', None),
    (1, '', 'adb: more than one device/emulator', None),
])
@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=True)
def test_package_availability_does_not_confuse_connection_failure_with_missing_app(_exists, code, stdout, stderr, expected):
    result = Mock(returncode=code, stdout=stdout, stderr=stderr)
    with patch('apps.launchers.android_app_launcher.subprocess.run', return_value=result) as run:
        assert AndroidAppLauncher().package_installed('com.panera.bread') is expected
    expected_command = ['/system/bin/pm', 'path', 'com.panera.bread'] if expected is True else ['adb', 'shell', 'pm', 'path', 'com.panera.bread']
    assert run.call_args.args[0] == expected_command


@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=False)
def test_waydroid_availability_unavailable_is_not_absent(_exists):
    waydroid = Mock()
    waydroid.list_apps.side_effect = WaydroidLauncherError('Session stopped')
    assert AndroidAppLauncher(waydroid=waydroid).package_installed('com.panera.bread') is None
    waydroid.launch_app.assert_not_called()


@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=True)
def test_local_positive_package_lookup_does_not_require_adb(_exists):
    result = Mock(returncode=0, stdout='package:/data/app/panera/base.apk\n', stderr='')
    with patch('apps.launchers.android_app_launcher.subprocess.run', return_value=result) as run:
        assert AndroidAppLauncher().package_installed('com.panera.bread') is True
    assert run.call_count == 1
    assert run.call_args.args[0] == ['/system/bin/pm', 'path', 'com.panera.bread']


@patch('apps.launchers.android_app_launcher.os.path.exists', return_value=True)
def test_filtered_local_package_lookup_is_not_proof_the_app_is_missing(_exists):
    local = Mock(returncode=1, stdout='', stderr='')
    offline = Mock(returncode=1, stdout='', stderr='adb: no devices/emulators found')
    with patch('apps.launchers.android_app_launcher.subprocess.run', side_effect=[local, offline]):
        assert AndroidAppLauncher().package_installed('com.panera.bread') is None
