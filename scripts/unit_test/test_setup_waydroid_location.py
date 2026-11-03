# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import json
import pytest
from scripts import setup_waydroid_location as setup


@pytest.mark.parametrize('uid', ['0', '2000'])
def test_explicit_setup_saves_original_permission_and_disable_restores_it(tmp_path, monkeypatch, uid):
    path = tmp_path / 'state/waydroid-location.json'
    monkeypatch.setattr(setup, 'configuration_path', lambda: path)
    calls = []

    def run(arguments):
        calls.append(arguments)
        if arguments == ['waydroid', 'status']:
            return 'IP address: 192.168.240.112'
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
        return 'Android phone'

    monkeypatch.setattr(setup, 'run', run)
    with pytest.raises(RuntimeError, match='not identified as Waydroid'):
        setup.setup('enable')
    assert not any(command[0] == 'sudo' for command in calls)
