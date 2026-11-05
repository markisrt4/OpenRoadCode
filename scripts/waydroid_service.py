# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Foreground user-service supervisor for the Linux/X11 Waydroid runtime."""
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
from threading import Event

from apps.launchers.waydroid_location_provider import configuration_path
from scripts.setup_waydroid_location import save
from scripts.waydroid_vm import WaydroidVM, android_address, owned_process

HELPER = '/usr/local/libexec/openroadcode-waydroid-prepare'


def privileged(vm, action):
    return vm.out('sudo', '-n', HELPER, action, timeout=240)


def configure_location(vm, serial):
    """Keep reversible settings and pin all runtime operations to this device."""
    def adb(*arguments):
        return vm.out('adb', '-s', serial, 'shell', *arguments)

    if 'waydroid' not in adb('getprop', 'ro.product.model').casefold():
        raise RuntimeError('The discovered ADB device is not Waydroid')
    uid = adb('id', '-u')
    if uid not in {'0', '2000'}:
        raise RuntimeError('Expected the Waydroid root or shell ADB identity')
    path = configuration_path()
    previous = json.loads(path.read_text()) if path.exists() else None
    if previous is not None and previous.get('mock_uid') != uid:
        raise RuntimeError('ADB identity changed; disable the previous location setup before restarting the service')
    if previous is None:
        modes = adb('cmd', 'appops', 'get', uid, 'android:mock_location')
        mode = re.search(r'MOCK_LOCATION:\s*(allow|deny|ignore|default|foreground)', modes, re.IGNORECASE)
        enabled = adb('cmd', 'location', 'is-location-enabled', '--user', '0')
        if enabled not in {'true', 'false'}:
            raise RuntimeError('Could not read the original Android location setting')
        previous = dict(mock_uid=uid, previous_mock_mode=mode[1].lower() if mode else 'default',
            previous_location_enabled=enabled)
    previous.update(serial=serial, enabled=False)
    save(path, previous)
    privileged(vm, 'location-root' if uid == '0' else 'location-shell')
    modes = adb('cmd', 'appops', 'get', uid, 'android:mock_location')
    if not re.search(r'MOCK_LOCATION:\s*allow\b', modes, re.IGNORECASE):
        raise RuntimeError('Android mock-location permission was not retained')
    if adb('cmd', 'location', 'is-location-enabled', '--user', '0') != 'true':
        raise RuntimeError('Android location is still disabled')
    if adb('pm', 'path', 'com.waze').startswith('package:'):
        package = adb('dumpsys', 'package', 'com.waze')
        for permission in ('ACCESS_COARSE_LOCATION', 'ACCESS_FINE_LOCATION'):
            if not re.search(r'android\.permission\.' + permission + r':\s*granted=true\b', package):
                raise RuntimeError('Waze location permission was not retained: ' + permission)
    previous['enabled'] = True
    save(path, previous)


def prepare(vm):
    if any(owned_process(record) for record in vm.state().values()) or vm.display_ready():
        raise RuntimeError('A manually managed Waydroid display/session is already running. Stop it before starting the service.')
    vm.desktop_preflight()
    if re.search(r'Session:\s*RUNNING', vm.out('waydroid', 'status', env=vm.environment)):
        raise RuntimeError('An unowned Waydroid session is running. Stop it before starting the service.')
    privileged(vm, 'container')
    vm.start_runtime(user_service=True)
    vm.out('adb', 'start-server', env=vm.environment)
    key = Path.home() / '.android/adbkey'
    if not key.exists():
        key.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        vm.out('adb', 'keygen', str(key))
    metadata = json.loads(privileged(vm, 'prepare'))
    # Parse with the same strict IPv4 validator as the interactive workflow.
    guest = android_address('inet ' + metadata['address'] + '/32')
    serial = f'{guest.ip}:5555'

    def connected():
        if vm.out('adb', '-s', serial, 'get-state', check=False, timeout=4) == 'device':
            return True
        vm.out('adb', 'disconnect', serial, check=False)
        vm.out('adb', 'connect', serial, check=False, timeout=12)
        return vm.out('adb', '-s', serial, 'get-state', check=False, timeout=4) == 'device'

    vm.wait('authorized Waydroid ADB', connected, attempts=3, timeout_s=45)
    configure_location(vm, serial)
    return serial


def notify_ready():
    address = os.environ.get('NOTIFY_SOCKET')
    if address:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as channel:
            channel.connect('\0' + address[1:] if address.startswith('@') else address)
            channel.sendall(b'READY=1\nSTATUS=Waydroid and location transport ready; awaiting a live host fix')


def supervise(vm, stop):
    serial = prepare(vm)
    notify_ready()
    vm.stage(f'Service ready: {serial}; ORC is started separately.')
    while not stop.wait(10):
        if not vm.display_ready() or any(not owned_process(record) for record in vm.state().values()):
            raise RuntimeError('Owned Waydroid display/session exited')
        if vm.out('adb', '-s', serial, 'get-state', check=False, timeout=4) != 'device':
            # Reconnect only this serial; never reset the desktop ADB server.
            vm.out('adb', 'disconnect', serial, check=False)
            vm.out('adb', 'connect', serial, check=False, timeout=12)
            if vm.out('adb', '-s', serial, 'get-state', check=False, timeout=4) != 'device':
                raise RuntimeError('Waydroid ADB connection lost; inspect the service journal')


def main():
    if os.geteuid() == 0:
        raise SystemExit('Run through the normal desktop user service')
    stop = Event()
    for name in (signal.SIGTERM, signal.SIGINT):
        signal.signal(name, lambda *_args: stop.set())
    vm = WaydroidVM()
    os.umask(0o077)
    try:
        with (vm.runtime / 'openroadcode-waydroid-vm.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Only clean up after ownership was checked, so a rejected manual
            # runtime is never stopped by the service's finally block.
            if any(owned_process(record) for record in vm.state().values()) or vm.display_ready():
                raise RuntimeError('Stop the manually managed Waydroid runtime before starting the service')
            try:
                supervise(vm, stop)
            finally:
                vm.stop()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Waydroid service failed: {error}') from error


if __name__ == '__main__':
    main()
