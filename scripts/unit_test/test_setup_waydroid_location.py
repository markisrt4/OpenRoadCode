# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import json
import subprocess
import pytest
from scripts import setup_waydroid_location as setup


@pytest.mark.parametrize('code', [0, 1, 255])
@pytest.mark.parametrize('stream', ['stdout', 'stderr'])
def test_android_help_usage_status_is_accepted_only_with_expected_capabilities(monkeypatch, code, stream):
    text = 'Location service commands:\n providers\n add-test-provider\n set-test-provider-location\n'
    result = subprocess.CompletedProcess([], code, text if stream == 'stdout' else '', text if stream == 'stderr' else '')
    monkeypatch.setattr(setup.subprocess, 'run', lambda *args, **kwargs: result)
    assert setup.run(['adb', '-s', '192.168.240.112:5555', 'shell', 'cmd', 'location', 'help']) == text.strip()


@pytest.mark.parametrize('text', ['adb: device unauthorized', 'Location service commands:\n providers',
    'Error: denied\nLocation service commands:\n providers add-test-provider set-test-provider-location'])
def test_bad_or_incomplete_help_still_fails(monkeypatch, text):
    monkeypatch.setattr(setup.subprocess, 'run', lambda *args, **kwargs: subprocess.CompletedProcess([], 1, text, ''))
    with pytest.raises(RuntimeError, match='Location setup command failed'):
        setup.run(['adb', '-s', '192.168.240.112:5555', 'shell', 'cmd', 'location', 'help'])


def test_help_text_cannot_mask_a_failed_location_mutation(monkeypatch):
    text = 'Location service commands:\n providers add-test-provider set-test-provider-location'
    monkeypatch.setattr(setup.subprocess, 'run', lambda *args, **kwargs: subprocess.CompletedProcess([], 255, text, ''))
    with pytest.raises(RuntimeError, match='Location setup command failed'):
        setup.run(['adb', '-s', '192.168.240.112:5555', 'shell', 'cmd', 'location', 'set-location-enabled', 'true'])


def test_status_reports_stale_device_and_denied_waze_permission_without_mutation(tmp_path, monkeypatch):
    path = tmp_path / 'location.json'
    path.write_text(json.dumps({'enabled': True, 'serial': '192.168.240.110:5555', 'mock_uid': '0'}))
    monkeypatch.setattr(setup, 'configuration_path', lambda: path)
    original = path.read_bytes()
    calls = []

    def run(arguments):
        calls.append(arguments)
        if arguments == ['waydroid', 'status']:
            return 'IP address: 192.168.240.112'
        if arguments[-1] == 'get-state':
            return 'device'
        if 'ro.product.model' in arguments:
            return 'WayDroid-x86_64-Device'
        if arguments[-2:] == ['id', '-u']:
            return '0'
        if 'is-location-enabled' in arguments:
            return 'true'
        if 'appops' in arguments:
            return 'MOCK_LOCATION: allow'
        return 'android.permission.ACCESS_FINE_LOCATION: granted=false\nandroid.permission.ACCESS_COARSE_LOCATION: granted=true'

    monkeypatch.setattr(setup, 'run', run)
    value = setup.location_status()
    assert value['configured_device_matches_session'] is False
    assert value['mock_location_permission'] == 'allow'
    assert value['access_fine_location'] is False
    assert value['access_coarse_location'] is True
    assert path.read_bytes() == original
    assert not any('sudo' in command or 'set' in command or 'connect' in command for command in calls)


@pytest.mark.parametrize('uid', ['0', '2000'])
def test_explicit_setup_saves_original_permission_and_disable_restores_it(tmp_path, monkeypatch, uid):
    path = tmp_path / 'state/waydroid-location.json'
    monkeypatch.setattr(setup, 'configuration_path', lambda: path)
    calls = []

    def run(arguments):
        calls.append(arguments)
        if arguments == ['waydroid', 'status']:
            return 'IP address: 192.168.240.112'
        if arguments[-1] == 'get-state':
            return 'device'
        if 'ro.product.model' in arguments:
            return 'WayDroid-x86_64-Device'
        if arguments[-1] == 'help':
            return 'add-test-provider set-test-provider-location'
        if arguments[-2:] == ['id', '-u']:
            return uid
        if 'get' in arguments:
            return 'MOCK_LOCATION: default'
        if 'is-location-enabled' in arguments:
            return 'false'
        return ''

    monkeypatch.setattr(setup, 'run', run)
    setup.setup('enable')
    value = json.loads(path.read_text())
    assert value['enabled'] is True
    assert value['previous_mock_mode'] == 'default'
    assert path.stat().st_mode & 0o777 == 0o600
    setup.setup('enable')
    assert json.loads(path.read_text())['previous_mock_mode'] == 'default'
    setup.setup('disable')
    assert not path.exists()
    assert any(command[-2:] == ['android:mock_location', 'default'] for command in calls)
    assert not any('set-test-provider-location' in command for command in calls)


def test_other_device_is_rejected_before_any_permission_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, 'configuration_path', lambda: tmp_path / 'location.json')
    calls = []

    def run(arguments):
        calls.append(arguments)
        if arguments == ['waydroid', 'status']:
            return 'IP address: 192.168.240.112'
        if arguments[-1] == 'get-state':
            return 'device'
        return 'Android phone'

    monkeypatch.setattr(setup, 'run', run)
    with pytest.raises(RuntimeError, match='not identified as Waydroid'):
        setup.setup('enable')
    assert not any(command[0] == 'sudo' for command in calls)


def test_vm_verified_serial_uses_live_container_ip_without_reconnecting_or_parsing_status(tmp_path, monkeypatch):
    path = tmp_path / 'location.json'
    monkeypatch.setattr(setup, 'configuration_path', lambda: path)
    calls = []

    def run(arguments):
        calls.append(arguments)
        assert arguments != ['waydroid', 'status']
        if arguments[-5:] == ['ip', '-4', 'addr', 'show', 'eth0']:
            return 'inet 192.168.240.123/24 brd 192.168.240.255 scope global eth0'
        if arguments[-1] == 'get-state':
            return 'device'
        if 'ro.product.model' in arguments:
            return 'WayDroid-x86_64-Device'
        if arguments[-2:] == ['id', '-u']:
            return '2000'
        if arguments[-1] == 'help':
            return 'add-test-provider set-test-provider-location'
        if 'is-location-enabled' in arguments:
            return 'false'
        return 'MOCK_LOCATION: default'

    monkeypatch.setattr(setup, 'run', run)
    setup.setup('enable', '192.168.240.123:5555')
    assert json.loads(path.read_text())['serial'] == '192.168.240.123:5555'
    assert not any(command[:2] == ['adb', 'connect'] for command in calls)


def test_live_container_address_still_rejects_a_different_explicit_device(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, 'configuration_path', lambda: tmp_path / 'location.json')
    calls = []

    def run(arguments):
        calls.append(arguments)
        return 'inet 192.168.240.112/24 scope global eth0'

    monkeypatch.setattr(setup, 'run', run)
    with pytest.raises(RuntimeError, match='does not match'):
        setup.setup('enable', '192.168.240.123:5555')
    assert len(calls) == 1


def test_missing_status_ip_falls_back_to_local_container_without_guessing_an_address(monkeypatch):
    def run(arguments):
        if arguments == ['waydroid', 'status']:
            return 'Session: RUNNING\nVendor type: MAINLINE'
        return 'inet 192.168.240.123/24 scope global eth0'

    monkeypatch.setattr(setup, 'run', run)
    assert setup.local_serial() == '192.168.240.123:5555'
