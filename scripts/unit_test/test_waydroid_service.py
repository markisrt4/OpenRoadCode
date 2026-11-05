# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import json
import os
import subprocess
from unittest.mock import Mock

import pytest

from scripts import install_waydroid_services as installer
from scripts import waydroid_service as service
from scripts import waydroid_service_privileged as helper


@pytest.mark.parametrize('uid,action', [('0', 'location-root'), ('2000', 'location-shell')])
def test_location_configuration_uses_pinned_identity_and_retains_original_settings(tmp_path, monkeypatch, uid, action):
    path = tmp_path / 'location.json'
    monkeypatch.setattr(service, 'configuration_path', lambda: path)
    configured = False

    def privileged(vm, requested):
        nonlocal configured
        assert requested == action
        configured = True

    def out(*arguments):
        assert arguments[:4] == ('adb', '-s', '192.168.240.112:5555', 'shell')
        if arguments[-1] == 'ro.product.model':
            return 'WayDroid-x86_64-Device'
        if arguments[-2:] == ('id', '-u'):
            return uid
        if 'appops' in arguments:
            return 'MOCK_LOCATION: ' + ('allow' if configured else 'default')
        return 'true' if configured else 'false'

    monkeypatch.setattr(service, 'privileged', privileged)
    vm = Mock(out=out)
    service.configure_location(vm, '192.168.240.112:5555')
    service.configure_location(vm, '192.168.240.112:5555')
    value = json.loads(path.read_text())
    assert value['enabled'] is True
    assert value['mock_uid'] == uid
    assert value['previous_mock_mode'] == 'default'
    assert value['previous_location_enabled'] == 'false'


def test_unretained_location_permission_leaves_configuration_disabled(tmp_path, monkeypatch):
    path = tmp_path / 'location.json'
    monkeypatch.setattr(service, 'configuration_path', lambda: path)
    monkeypatch.setattr(service, 'privileged', Mock())

    def out(*arguments):
        if arguments[-1] == 'ro.product.model':
            return 'WayDroid device'
        if arguments[-2:] == ('id', '-u'):
            return '2000'
        if 'appops' in arguments:
            return 'MOCK_LOCATION: ignore'
        return 'false'

    with pytest.raises(RuntimeError, match='not retained'):
        service.configure_location(Mock(out=out), '192.168.240.112:5555')
    assert json.loads(path.read_text())['enabled'] is False


def test_other_android_device_is_rejected_before_privileged_location_changes(monkeypatch):
    privileged = Mock()
    monkeypatch.setattr(service, 'privileged', privileged)
    with pytest.raises(RuntimeError, match='not Waydroid'):
        service.configure_location(Mock(out=Mock(return_value='Samsung phone')), '192.168.240.112:5555')
    privileged.assert_not_called()


def test_service_cannot_be_ready_with_installed_waze_location_permission_denied(tmp_path, monkeypatch):
    path = tmp_path / 'location.json'
    monkeypatch.setattr(service, 'configuration_path', lambda: path)
    monkeypatch.setattr(service, 'privileged', Mock())

    def out(*arguments):
        if arguments[-1] == 'ro.product.model':
            return 'WayDroid device'
        if arguments[-2:] == ('id', '-u'):
            return '2000'
        if 'appops' in arguments:
            return 'MOCK_LOCATION: allow'
        if arguments[-3:] == ('pm', 'path', 'com.waze'):
            return 'package:/data/app/com.waze/base.apk'
        if 'dumpsys' in arguments:
            return 'android.permission.ACCESS_COARSE_LOCATION: granted=true\nandroid.permission.ACCESS_FINE_LOCATION: granted=false'
        return 'true'

    with pytest.raises(RuntimeError, match='ACCESS_FINE_LOCATION'):
        service.configure_location(Mock(out=out), '192.168.240.112:5555')
    assert json.loads(path.read_text())['enabled'] is False


def test_service_does_not_adopt_manually_managed_runtime():
    vm = Mock()
    vm.state.return_value = {}
    vm.display_ready.return_value = True
    with pytest.raises(RuntimeError, match='manually managed'):
        service.prepare(vm)
    vm.desktop_preflight.assert_not_called()


def test_lost_adb_reconnects_only_selected_device_then_reports_failure(monkeypatch):
    vm = Mock()
    vm.state.return_value = {}
    vm.display_ready.return_value = True
    vm.out.return_value = 'offline'
    monkeypatch.setattr(service, 'prepare', lambda vm: '192.168.240.112:5555')
    ready = Mock()
    monkeypatch.setattr(service, 'notify_ready', ready)
    stop = Mock()
    stop.wait.return_value = False
    with pytest.raises(RuntimeError, match='connection lost'):
        service.supervise(vm, stop)
    ready.assert_called_once()
    commands = [call.args for call in vm.out.call_args_list]
    assert ('adb', 'connect', '192.168.240.112:5555') in commands
    assert ('adb', 'disconnect', '192.168.240.112:5555') in commands
    assert not any('kill-server' in command or command == ('adb', 'disconnect') for command in commands)


def test_units_keep_ui_and_runtime_lifecycles_separate():
    runtime = installer.render('openroadcode-waydroid.service')
    ui = installer.render('openroadcode-ui.service')
    assert 'Type=notify' in runtime
    assert 'scripts.waydroid_service' in runtime
    assert 'runOrcUi' not in runtime
    assert 'Restart=on-failure' in runtime
    assert 'After=openroadcode-waydroid.service' in ui
    assert 'runOrcUi' in ui
    assert 'BindsTo=' not in ui and 'Requires=' not in ui
    assert 'openroadcode-ui' not in runtime
    assert f'WorkingDirectory={installer.ROOT}\n' in runtime


def test_sudo_grant_contains_only_fixed_installed_helper_operations():
    rules = installer.sudoers('markis')
    assert len(rules.splitlines()) == 4
    assert '*' not in rules and '/workspace' not in rules
    assert all(installer.HELPER in line for line in rules.splitlines())
    with pytest.raises(ValueError):
        installer.sudoers('someone ALL=(ALL) ALL')
    assert (installer.ROOT / 'scripts/waydroid_service_privileged.py').read_text().startswith('#!/usr/bin/python3 -I\n')


def test_installer_quotes_paths_for_systemd_without_expanding_user_path():
    assert installer.systemd_quote('/home/test/$dir%name', command=True) == '"/home/test/$$dir%%name"'
    assert installer.systemd_quote('/home/test/$dir%name') == '"/home/test/$dir%%name"'
    with pytest.raises(ValueError):
        installer.systemd_quote('bad\npath')


def test_privileged_helper_rejects_unknown_action_without_running_commands(monkeypatch):
    run = Mock()
    monkeypatch.setattr(helper, 'run', run)
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 0)
    monkeypatch.setattr('sys.argv', ['helper', 'shell', 'arbitrary command'])
    with pytest.raises(SystemExit):
        helper.main()
    run.assert_not_called()


def test_invalid_public_key_cannot_change_android_authorization(tmp_path, monkeypatch):
    (tmp_path / '.android').mkdir()
    (tmp_path / '.android/adbkey.pub').write_text('not-a-key\nsecond-line')
    android = Mock()
    monkeypatch.setattr(helper, 'android', android)
    with pytest.raises(RuntimeError, match='Invalid ADB public key'):
        helper.authorize(tmp_path)
    android.assert_not_called()


def test_installer_does_not_start_orc_or_services_implicitly(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    calls = []
    monkeypatch.setattr(installer, 'run', lambda *args: calls.append(args))
    monkeypatch.setattr(installer.subprocess, 'run', Mock(return_value=Mock(stdout='inactive')))
    installer.install()
    assert not any('start' in call or 'openroadcode-ui.service' in call for call in calls)
    assert (tmp_path / 'systemd/user/openroadcode-ui.service').exists()
    assert (tmp_path / 'autostart/openroadcode-waydroid.desktop').exists()


def test_installer_refuses_to_replace_helper_while_runtime_is_active(monkeypatch):
    run = Mock()
    monkeypatch.setattr(installer, 'run', run)
    monkeypatch.setattr(installer.subprocess, 'run', Mock(return_value=Mock(stdout='active')))
    with pytest.raises(RuntimeError, match='before upgrading'):
        installer.install()
    run.assert_not_called()


def test_prepare_uses_container_address_when_waydroid_status_omits_it(tmp_path, monkeypatch):
    key = tmp_path / '.android/adbkey'
    key.parent.mkdir()
    key.write_text('existing private key must not be read')
    monkeypatch.setattr(service.Path, 'home', lambda: tmp_path)
    vm = Mock()
    vm.state.return_value = {}
    vm.display_ready.return_value = False
    vm.out.return_value = 'device'
    vm.wait.side_effect = lambda description, predicate, **kwargs: predicate()
    privileged = Mock(side_effect=['', '{"address":"192.168.240.123"}'])
    configure = Mock()
    monkeypatch.setattr(service, 'privileged', privileged)
    monkeypatch.setattr(service, 'configure_location', configure)
    assert service.prepare(vm) == '192.168.240.123:5555'
    vm.start_runtime.assert_called_once_with(user_service=True)
    configure.assert_called_once_with(vm, '192.168.240.123:5555')
    assert sum(call.args[:2] == ('waydroid', 'status') for call in vm.out.call_args_list) == 1


def test_failed_service_start_cleans_owned_resources_without_notifying_ready(tmp_path, monkeypatch):
    vm = Mock(runtime=tmp_path)
    vm.state.return_value = {}
    vm.display_ready.return_value = False
    monkeypatch.setattr(service, 'WaydroidVM', lambda: vm)
    monkeypatch.setattr(service.os, 'geteuid', lambda: 1001)
    monkeypatch.setattr(service.signal, 'signal', Mock())
    monkeypatch.setattr(service, 'prepare', Mock(side_effect=RuntimeError('ADB unavailable')))
    ready = Mock()
    monkeypatch.setattr(service, 'notify_ready', ready)
    with pytest.raises(SystemExit, match='ADB unavailable'):
        service.main()
    vm.stop.assert_called_once_with()
    ready.assert_not_called()


def test_rejected_manual_runtime_is_not_cleaned_up_by_service(tmp_path, monkeypatch):
    vm = Mock(runtime=tmp_path)
    vm.state.return_value = {}
    vm.display_ready.return_value = True
    monkeypatch.setattr(service, 'WaydroidVM', lambda: vm)
    monkeypatch.setattr(service.os, 'geteuid', lambda: 1001)
    monkeypatch.setattr(service.signal, 'signal', Mock())
    with pytest.raises(SystemExit, match='manually managed'):
        service.main()
    vm.stop.assert_not_called()


def test_network_helper_keeps_existing_nat_and_scopes_forwarding_to_bridge(monkeypatch):
    commands = []

    def run(*args, **kwargs):
        commands.append(args)
        output = ''
        if args[:4] == ('ip', '-j', '-4', 'addr'):
            output = '[{"addr_info":[{"family":"inet","local":"192.168.240.1","prefixlen":24}]}]'
        elif args[:4] == ('ip', '-j', 'route', 'get'):
            output = '[{"dev":"waydroid0"}]'
        elif args[:4] == ('ip', '-j', 'link', 'show'):
            output = '[{"ifindex":23,"ifname":"vethExact"}]'
        elif '-S' in args:
            output = '-A POSTROUTING -s 192.168.240.0/24 -j MASQUERADE'
        return Mock(stdout=output, returncode=0)

    monkeypatch.setattr(helper, 'run', run)
    monkeypatch.setattr(helper, 'android', lambda *args: '23' if args[0] == 'cat' else 'inet 192.168.240.112/24')
    monkeypatch.setattr(helper.shutil, 'which', lambda name: None if name == 'nmcli' else '/usr/sbin/' + name)
    assert helper.prepare_network() == '192.168.240.112'
    checks = [command for command in commands if '-C' in command]
    assert len(checks) == 4
    assert all('waydroid0' in command and '192.168.240.0/24' in command for command in checks)
    assert not any('-A' in command or '-F' in command or '-P' in command for command in commands)


@pytest.mark.parametrize('display,expected', [(':7', ':7'), ('', ':0')])
def test_linux_launcher_preserves_the_services_actual_desktop_display(tmp_path, display, expected):
    interpreter = tmp_path / 'fake-python'
    interpreter.write_text('#!/bin/sh\nprintf "%s" "$DISPLAY"\n')
    interpreter.chmod(0o755)
    environment = dict(os.environ, PYTHON=str(interpreter), DISPLAY=display)
    environment.pop('TERMUX_VERSION', None)
    environment.pop('PREFIX', None)
    result = subprocess.run(['bash', str(installer.ROOT / 'runOrcUi')], env=environment,
        capture_output=True, text=True, timeout=5, check=True)
    assert result.stdout == expected
