# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import subprocess
from unittest.mock import patch
import pytest

from apps.launchers.waydroid_location_provider import WaydroidLocationProvider
from ui.navigation import GeoPoint


def test_targets_only_configured_waydroid_and_removes_only_its_own_provider():
    provider = WaydroidLocationProvider('192.168.240.112:5555')
    with patch('apps.launchers.waydroid_location_provider.subprocess.run') as run:
        run.return_value = subprocess.CompletedProcess([], 0, 'WayDroid-x86_64-Device', '')
        provider.clear_location()
        run.assert_not_called()
        provider.send_location(GeoPoint(0, 0), 50)
        provider.clear_location()
        provider.clear_location()
    commands = [call.args[0] for call in run.call_args_list]
    assert all(command[:3] == ['adb', '-s', '192.168.240.112:5555'] for command in commands)
    assert sum('remove-test-provider' in command for command in commands) == 1
    assert '0.00000000,0.00000000' in commands[-2]
    assert not provider._owns_provider


def test_wrong_device_is_rejected_before_any_location_change():
    provider = WaydroidLocationProvider('192.168.240.112:5555')
    with patch('apps.launchers.waydroid_location_provider.subprocess.run', return_value=
               subprocess.CompletedProcess([], 0, 'Samsung phone', '')) as run:
        with pytest.raises(RuntimeError, match='not Waydroid'):
            provider.send_location(GeoPoint(0, 0), 50)
    assert run.call_count == 1
    assert not provider._owns_provider
