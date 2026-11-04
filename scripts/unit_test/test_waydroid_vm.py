# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Exercise lifecycle decisions with command fakes; never mutate the test host."""
import base64
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import Mock

import pytest

from scripts import waydroid_vm as module


class Commands:
    def __init__(self):
        self.calls = []
        self.rules = set()
        self.guest = '192.168.240.112/24'
        self.authorized = True
        self.connected = False
        self.keys = 'existing-key-without-a-newline'
        self.legacy_nat = True
        self.session_running = True

    def __call__(self, arguments, **options):
        self.calls.append((arguments, options))
        output, code = '', 0
        if arguments == ['waydroid', 'status']:
            output = 'Session: ' + ('RUNNING' if self.session_running else 'STOPPED') + '\nIP address: 192.168.240.112'
        elif arguments == ['waydroid', 'session', 'stop']:
            self.session_running = False
        elif arguments[:5] == ['ip', '-j', '-4', 'addr', 'show']:
            output = json.dumps([{'addr_info': [{'family': 'inet', 'local': '192.168.240.1', 'prefixlen': 24}]}])
        elif arguments[:4] == ['ip', '-j', 'link', 'show']:
            output = '[{"ifindex":23,"ifname":"vethCurrent"}]'
        elif arguments[:4] == ['ip', '-j', 'route', 'get']:
            output = '[{"dev":"waydroid0"}]'
        elif arguments[:2] == ['nmcli', '-t']:
            output = 'running\n'
        elif arguments[:5] == ['sudo', '-n', 'waydroid', 'shell', '--']:
            android = arguments[5:]
            if android == ['ip', '-4', 'addr', 'show', 'eth0']:
                output = 'inet ' + self.guest + ' scope global eth0'
            elif android == ['cat', '/sys/class/net/eth0/iflink']:
                output = '23'
            elif android == ['cat', '/data/misc/adb/adb_keys']:
                output = self.keys
            elif android[:2] == ['tee', '-a']:
                self.keys += options['input']
            elif android == ['getprop', 'init.svc.adbd']:
                output = 'running'
            elif android == ['getprop', 'sys.boot_completed']:
                output = '1'
            elif android == ['ss', '-lnt']:
                output = 'LISTEN 0 4 *:5555 *:*'
            elif android == ['locksettings', 'get-disabled']:
                output = 'true'
        elif len(arguments) > 2 and arguments[2] in ('iptables', 'iptables-legacy'):
            if '-C' in arguments:
                code = 0 if (arguments[2], tuple(arguments[arguments.index('-C') + 1:])) in self.rules else 1
            elif '-I' in arguments:
                index = arguments.index('-I')
                self.rules.add((arguments[2], tuple([arguments[index + 1], *arguments[index + 3:]])))
            elif '-S' in arguments and arguments[2] == 'iptables-legacy' and self.legacy_nat:
                output = '-A POSTROUTING -s 192.168.240.0/24 ! -d 192.168.240.0/24 -j MASQUERADE'
        elif arguments[:2] == ['adb', 'connect']:
            self.connected = self.authorized
            output = 'connected to ' + arguments[-1]  # Deliberately misleading on auth failure.
        elif arguments[0] == 'adb' and arguments[-1] == 'get-state':
            output = 'device' if self.connected else 'offline'
        elif arguments[0] == 'adb' and arguments[-1] == 'ro.product.model':
            output = 'WayDroid_x86_64_Device'
        return subprocess.CompletedProcess(arguments, code, output, '')


@pytest.fixture
def vm(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_RUNTIME_DIR', str(tmp_path))
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'state'))
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(module.shutil, 'which', lambda name: '/usr/bin/' + name)
    commands = Commands()
    return module.WaydroidVM(runner=commands, sleeper=lambda _: None), commands


def install_key(tmp_path):
    key = tmp_path / '.android/adbkey'
    key.parent.mkdir()
    key.write_text('private-key-not-read-by-the-workflow')
    public = base64.b64encode(bytes(524)).decode() + ' desktop@vm'
    key.with_suffix('.pub').write_text(public)
    return public


def test_network_is_idempotent_and_does_not_change_unrelated_interfaces_or_policies(vm):
    runtime, commands = vm
    runtime.configure_network()
    before = len([args for args, _ in commands.calls if '-I' in args])
    runtime.configure_network()
    assert len([args for args, _ in commands.calls if '-I' in args]) == before == 4
    assert not any('-F' in args or '-P' in args for args, _ in commands.calls)
    managed = [args[-3:] for args, _ in commands.calls if 'managed' in args]
    assert managed == [['waydroid0', 'managed', 'no'], ['vethCurrent', 'managed', 'no']] * 2
    assert not any('-A' in args and 'MASQUERADE' in args for args, _ in commands.calls)
    assert runtime.environment['ANDROID_SERIAL'] == '192.168.240.112:5555'


def test_changed_ip_is_discovered_and_wrong_subnet_fails_before_firewall_mutation(vm):
    runtime, commands = vm
    commands.guest = '192.168.240.123/24'
    runtime.configure_network()
    assert runtime.environment['ANDROID_SERIAL'] == '192.168.240.123:5555'
    commands.calls.clear()
    commands.guest = '10.0.0.9/24'
    with pytest.raises(RuntimeError, match='same subnet'):
        runtime.configure_network()
    assert not any('iptables' in args or 'iptables-legacy' in args for args, _ in commands.calls)


def test_missing_nat_adds_only_the_waydroid_subnet_rule(vm):
    runtime, commands = vm
    commands.legacy_nat = False
    runtime.configure_network()
    rules = [args for args, _ in commands.calls if '-A' in args]
    assert len(rules) == 1
    assert rules[0][-11:] == ['-s', '192.168.240.0/24', '!', '-d', '192.168.240.0/24',
                            '-m', 'comment', '--comment', module.RULE_COMMENT, '-j', 'MASQUERADE']


def test_key_import_preserves_existing_keys_and_rerun_does_not_duplicate(vm, tmp_path):
    runtime, commands = vm
    public = install_key(tmp_path)
    guest = module.android_address('inet 192.168.240.112/24')
    runtime.configure_adb(guest)
    assert commands.keys == 'existing-key-without-a-newline\n' + public + '\n'
    count = len([args for args, _ in commands.calls if 'tee' in args])
    runtime.configure_adb(guest)
    assert len([args for args, _ in commands.calls if 'tee' in args]) == count == 1
    start = next(options for args, options in commands.calls if args == ['adb', 'start-server'])
    assert start['env']['ADB_LOCAL_TRANSPORT_MAX_PORT'] == '5555'
    assert not any('kill-server' in args or 'ro.adb.secure' in args for args, _ in commands.calls)


def test_connected_message_is_not_accepted_when_adb_stays_offline(vm, tmp_path):
    runtime, commands = vm
    install_key(tmp_path)
    commands.authorized = False
    with pytest.raises(RuntimeError, match='authorized Waydroid ADB'):
        runtime.configure_adb(module.android_address('inet 192.168.240.112/24'))
    assert len([args for args, _ in commands.calls if args[:2] == ['adb', 'connect']]) == 3


def test_reused_pid_is_never_signalled(vm, monkeypatch):
    runtime, _ = vm
    runtime.save({'display_launcher': {'pid': 123, 'started': '1'}})
    monkeypatch.setattr(module, 'process_identity', lambda _: {'pid': 123, 'started': '2'})
    kill = Mock()
    monkeypatch.setattr(module.os, 'kill', kill)
    runtime.stop()
    kill.assert_not_called()


def test_dead_socket_is_reclaimed_but_a_live_socket_is_preserved(vm):
    runtime, _ = vm
    path = runtime.runtime / runtime.display
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(str(path))
        server.listen()
        runtime.reclaim_stale_display()
        assert path.exists()
    runtime.reclaim_stale_display()
    assert not path.exists()


def test_legacy_display_is_not_replaced_and_no_service_is_started(vm, monkeypatch):
    runtime, commands = vm
    monkeypatch.setattr(runtime, 'desktop_preflight', lambda: None)
    (runtime.runtime / runtime.display).touch()
    with pytest.raises(RuntimeError, match='legacy compositor'):
        runtime.start_runtime()
    assert not any('systemctl' in args for args, _ in commands.calls)


def test_waydroid_shell_success_exit_cannot_mask_an_android_command_error(vm):
    runtime, _ = vm
    runtime.command = lambda args, **kwargs: subprocess.CompletedProcess(args, 0, 'RTNETLINK answers: Network is unreachable', '')
    with pytest.raises(RuntimeError, match='Android command failed'):
        runtime.android('ip', 'route', 'replace')


def test_status_does_not_start_an_adb_server_or_repair_network(vm, monkeypatch):
    runtime, commands = vm
    monkeypatch.setattr(module.socket, 'create_connection', Mock(side_effect=ConnectionRefusedError))
    report = runtime.status()
    assert report['adb_state'] == 'host ADB server is not running'
    assert not any(args[0] == 'adb' or 'sysctl' in args or 'systemctl' in args for args, _ in commands.calls)


def test_complete_configuration_enables_location_only_after_verified_adb(vm, tmp_path, monkeypatch):
    runtime, commands = vm
    install_key(tmp_path)
    monkeypatch.setattr(runtime, 'start_runtime', lambda: None)
    location = Mock()
    monkeypatch.setattr(module, 'setup_location', location)
    assert runtime.configure() == '192.168.240.112:5555'
    location.assert_called_once_with('enable', '192.168.240.112:5555')
    assert any(args[-3:] == ['locksettings', 'set-disabled', 'true'] for args, _ in commands.calls)
    assert any(args[-4:] == ['svc', 'power', 'stayon', 'true'] for args, _ in commands.calls)


def test_ready_runtime_is_reused_without_new_display_or_session(vm, monkeypatch):
    runtime, commands = vm
    monkeypatch.setattr(runtime, 'desktop_preflight', lambda: None)
    monkeypatch.setattr(runtime, 'display_ready', lambda: True)
    spawn = Mock()
    monkeypatch.setattr(runtime, 'spawn', spawn)
    runtime.start_runtime()
    spawn.assert_not_called()
    assert any(args[-3:] == ['systemctl', 'start', 'waydroid-container'] for args, _ in commands.calls)


def test_corrupt_pid_record_cannot_be_used_for_stop(vm, monkeypatch):
    runtime, _ = vm
    runtime.save({'display_launcher': {'pid': -1, 'started': '2'}})
    kill = Mock()
    monkeypatch.setattr(module.os, 'kill', kill)
    with pytest.raises(RuntimeError, match='Invalid managed runtime PID'):
        runtime.stop()
    kill.assert_not_called()


def test_stuck_adbd_recovery_targets_only_the_android_daemon(vm, tmp_path):
    runtime, commands = vm
    install_key(tmp_path)
    stuck = [True]

    def run(arguments, **options):
        if arguments[-2:] == ['getprop', 'init.svc.adbd'] and stuck[0]:
            return subprocess.CompletedProcess(arguments, 0, 'stopping', '')
        if arguments[-3:] == ['killall', '-9', 'adbd']:
            stuck[0] = False
        return commands(arguments, **options)

    runtime.command = run
    runtime.configure_adb(module.android_address('inet 192.168.240.112/24'))
    assert any(args == ['sudo', '-n', 'waydroid', 'shell', '--', 'killall', '-9', 'adbd'] for args, _ in commands.calls)
    assert not any('kill-server' in args or 'systemctl' in args for args, _ in commands.calls)


def test_explicit_restart_rebuilds_container_but_preserves_display_record_and_host_adb(vm, monkeypatch):
    runtime, commands = vm
    display = {'pid': 123, 'started': '1'}
    runtime.save({'display_launcher': display, 'session': {'pid': 124, 'started': '2'}})
    monkeypatch.setattr(runtime, 'display_ready', lambda: True)
    runtime.restart()
    assert runtime.state() == {'display_launcher': display}
    assert any(args == ['sudo', '-n', 'systemctl', 'restart', 'waydroid-container'] for args, _ in commands.calls)
    assert not any('adb' in args or 'weston' in args for args, _ in commands.calls)


@pytest.mark.parametrize('window_pid,windows,ready', [('', '81788933', True),
    ('123', '81788933', True), ('999', '81788933', False), ('', '81788933\n81788934', False)])
def test_weston_readiness_allows_missing_x11_pid_but_rejects_mismatch_and_ambiguity(vm, monkeypatch, window_pid, windows, ready):
    runtime, commands = vm
    (runtime.runtime / runtime.display).touch()
    (runtime.runtime / 'openroadcode-waydroid-kiosk').write_text('123')
    original_read = Path.read_bytes

    def read(path):
        if str(path) == '/proc/123/cmdline':
            return b'weston\0--shell=kiosk-shell.so\0--idle-time=0\0--socket=wayland-0\0'
        return original_read(path)

    def run(arguments, **options):
        if arguments[:2] == ['xdotool', 'search']:
            return subprocess.CompletedProcess(arguments, 0, windows, '')
        if arguments[:2] == ['xdotool', 'getwindowpid']:
            return subprocess.CompletedProcess(arguments, 0 if window_pid else 1, window_pid, '')
        return commands(arguments, **options)

    monkeypatch.setattr(Path, 'read_bytes', read)
    runtime.command = run
    assert runtime.display_ready() is ready
