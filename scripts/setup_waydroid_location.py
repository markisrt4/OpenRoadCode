#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Explicit, reversible mock-location setup for the local Waydroid instance."""
import argparse
import json
import ipaddress
import os
import re
import subprocess

from apps.launchers.waydroid_location_provider import configuration_path


def run(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=15, check=False)
    output = result.stdout + result.stderr
    location_help = arguments[0] == 'adb' and arguments[-4:] == ['shell', 'cmd', 'location', 'help']
    # Some Android images return ShellCommand's usage status (1 or 255) even
    # after printing valid help, sometimes to stderr. Accept only this precise
    # read-only probe with the required location-provider capabilities present.
    valid_help = (location_help and result.returncode in (0, 1, 255)
                  and 'Location service commands:' in output
                  and all(value in output for value in ('providers', 'add-test-provider', 'set-test-provider-location')))
    if (result.returncode and not valid_help) or any(value in output for value in ('Exception', 'Error:', 'Unknown command')):
        raise RuntimeError('Location setup command failed: ' + ' '.join(arguments[:5]) + '\n' + output)
    return output.strip() if location_help else result.stdout.strip()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
    temporary.replace(path)


def local_serial(*, from_container=False):
    """Use live eth0 when status omits its IP or a caller pins a verified device."""
    if not from_container:
        status = run(['waydroid', 'status'])
        status = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', status)
        match = re.search(r'^\s*IP address:\s*(\d+\.\d+\.\d+\.\d+)\s*$', status, re.MULTILINE)
        if match is not None:
            return str(ipaddress.IPv4Address(match[1])) + ':5555'
    address = run(['sudo', '-n', 'waydroid', 'shell', '--', 'ip', '-4', 'addr', 'show', 'eth0'])
    match = re.search(r'\binet\s+(\d+\.\d+\.\d+\.\d+)/\d+\b', address)
    if match is None:
        raise RuntimeError('The local Waydroid eth0 interface has no IPv4 address. Wait for Android networking, then retry.')
    return str(ipaddress.IPv4Address(match[1])) + ':5555'


def location_status():
    """Read only configuration and permission flags; never collect coordinates."""
    path = configuration_path()
    configuration = json.loads(path.read_text()) if path.exists() else {}
    report = {'configured': configuration.get('enabled') is True}
    try:
        serial = local_serial()
    except RuntimeError:
        report['android_connection'] = 'Local Android address unavailable; run sudo -v for container inspection'
        return report
    report['configured_device_matches_session'] = configuration.get('serial') == serial
    report['android_connection'] = 'unavailable'
    try:
        model = run(['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model'])
        if 'waydroid' not in model.casefold():
            report['android_connection'] = 'Device is not Waydroid'
            return report
        report['android_connection'] = 'connected'
        report['location_enabled'] = run(['adb', '-s', serial, 'shell', 'cmd', 'location',
                                          'is-location-enabled', '--user', '0'])
        uid = run(['adb', '-s', serial, 'shell', 'id', '-u'])
        report['configured_identity_matches'] = configuration.get('mock_uid') == uid
        modes = run(['adb', '-s', serial, 'shell', 'cmd', 'appops', 'get', uid, 'android:mock_location'])
        mode = re.search(r'MOCK_LOCATION:\s*(allow|deny|ignore|default|foreground)', modes, re.IGNORECASE)
        report['mock_location_permission'] = mode[1].lower() if mode else 'not explicitly allowed'
        package = run(['adb', '-s', serial, 'shell', 'dumpsys', 'package', 'com.waze'])
        for permission in ('ACCESS_FINE_LOCATION', 'ACCESS_COARSE_LOCATION'):
            granted = re.search(r'android.permission.' + permission + r':\s*granted=(true|false)', package)
            report[permission.lower()] = granted[1] == 'true' if granted else 'unavailable'
    except RuntimeError:
        report['diagnostic_error'] = 'Could not read Android connection or permissions; rerun location setup with Waydroid running'
    return report


def setup(action, serial=None):
    path = configuration_path()
    previous = json.loads(path.read_text()) if path.exists() else None
    if action == 'disable' and previous is None:
        return
    expected = local_serial(from_container=serial is not None)
    if serial is not None and serial != expected:
        raise RuntimeError('The selected ADB device does not match the local Waydroid session.')
    if serial is None:
        run(['adb', 'connect', expected])
    serial = expected
    if run(['adb', '-s', serial, 'get-state']) != 'device':
        raise RuntimeError('The local Waydroid ADB connection is not authorized/ready.')
    model = run(['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model'])
    if 'waydroid' not in model.casefold():
        raise RuntimeError('The selected Android device is not identified as Waydroid.')
    if action == 'disable':
        run(['sudo', 'waydroid', 'shell', '--', 'cmd', 'appops', 'set', previous['mock_uid'],
             'android:mock_location', previous['previous_mock_mode']])
        run(['adb', '-s', serial, 'shell', 'cmd', 'location', 'set-location-enabled',
             previous['previous_location_enabled'], '--user', '0'])
        path.unlink()
        return
    uid = run(['adb', '-s', serial, 'shell', 'id', '-u'])
    if uid not in {'0', '2000'}:
        raise RuntimeError('Expected the Waydroid ADB root or shell identity.')
    if previous is not None and previous['mock_uid'] != uid:
        raise RuntimeError('The Android ADB identity changed. Disable the old location setup before enabling again.')
    help_text = run(['adb', '-s', serial, 'shell', 'cmd', 'location', 'help'])
    if 'add-test-provider' not in help_text or 'set-test-provider-location' not in help_text:
        raise RuntimeError('This Android image does not expose the expected location-provider commands.')
    if previous is None:
        modes = run(['sudo', 'waydroid', 'shell', '--', 'cmd', 'appops', 'get',
                     uid, 'android:mock_location'])
        mode = re.search(r'MOCK_LOCATION:\s*(allow|deny|ignore|default|foreground)', modes, re.IGNORECASE)
        previous = dict(mock_uid=uid, previous_mock_mode=mode[1].lower() if mode else 'default',
            previous_location_enabled=run(['adb', '-s', serial, 'shell', 'cmd', 'location',
                                          'is-location-enabled', '--user', '0']))
        if previous['previous_location_enabled'] not in {'true', 'false'}:
            raise RuntimeError('Could not read the original Android location setting; no settings were changed.')
    previous.update(serial=serial, enabled=False)
    save(path, previous)
    run(['sudo', 'waydroid', 'shell', '--', 'cmd', 'appops', 'set', uid, 'android:mock_location', 'allow'])
    run(['adb', '-s', serial, 'shell', 'cmd', 'location', 'set-location-enabled', 'true', '--user', '0'])
    previous['enabled'] = True
    save(path, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('enable', 'disable', 'status'))
    parser.add_argument('--serial')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the normal desktop user; only setup commands use sudo.')
    try:
        if args.action == 'status':
            print(json.dumps(location_status(), indent=2))
            return
        setup(args.action, args.serial)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
    print('Waydroid location sharing ' + ('configured. Restart ORC to use it.' if args.action == 'enable' else 'disabled.'))


if __name__ == '__main__':
    main()
