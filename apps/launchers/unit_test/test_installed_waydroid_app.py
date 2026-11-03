# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import Mock

from apps.launchers.installed_waydroid_app import InstalledWaydroidAppLauncher
from apps.launchers.waydroid_launcher import AndroidApp, WaydroidLauncherError


def test_launches_exact_installed_package_and_returns_its_name():
    waydroid = Mock()
    waydroid.list_apps.return_value = (AndroidApp('Waze helper', 'com.waze.helper'),
                                      AndroidApp('Waze', 'com.waze'))
    assert InstalledWaydroidAppLauncher(waydroid).launch_installed_app('com.waze') == 'Waze'
    waydroid.launch_app.assert_called_once_with('com.waze')


def test_missing_package_or_unavailable_runtime_returns_no_app():
    waydroid = Mock()
    waydroid.list_apps.return_value = ()
    launcher = InstalledWaydroidAppLauncher(waydroid)
    assert launcher.launch_installed_app('com.waze') is None
    waydroid.launch_app.assert_not_called()
    waydroid.list_apps.side_effect = WaydroidLauncherError('unavailable')
    assert launcher.launch_installed_app('com.waze') is None


def test_destination_intent_does_not_get_replaced_by_plain_app_launch():
    waydroid = Mock()
    waydroid.list_apps.return_value = (AndroidApp('Waze', 'com.waze'),)
    uri = 'waze://?ll=42.5,-83&navigate=yes'
    assert InstalledWaydroidAppLauncher(waydroid).launch_installed_app('com.waze', uri=uri) == 'Waze'
    waydroid.launch_uri.assert_called_once_with(uri)
    waydroid.launch_app.assert_not_called()
