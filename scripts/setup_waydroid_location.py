#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Explicit, reversible mock-location setup for the local Waydroid instance."""
import argparse
import json
import os
import re
import subprocess

from apps.launchers.waydroid_location_provider import configuration_path


def run(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=15, check=False)
    output = result.stdout + result.stderr
    if result.returncode or any(value in output for value in ('Exception', 'Error:', 'Unknown command')):
        raise RuntimeError('Location setup command failed: ' + ' '.join(arguments[:5]) + '\n' + output)
    return result.stdout.strip()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
    temporary.replace(path)


def setup(action, serial=None):
    path = configuration_path()
    previous = json.loads(path.read_text()) if path.exists() else None
    if action == 'disable' and previous is None:
        return
    status = run(['waydroid', 'status'])
    match = re.search(r'^\s*IP address:\s*(\d+\.\d+\.\d+\.\d+)\s*$', status, re.MULTILINE)
    if match is None:
        raise RuntimeError('Start the local Waydroid session and wait until it has an IP address.')
    expected = match[1] + ':5555'
    if serial is not None and serial != expected:
        raise RuntimeError('The selected ADB device does not match the local Waydroid session.')
    serial = expected
    run(['waydroid', 'adb', 'connect'])
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
    parser.add_argument('action', choices=('enable', 'disable'))
    parser.add_argument('--serial')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the normal desktop user; only setup commands use sudo.')
    try:
        setup(args.action, args.serial)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
    print('Waydroid location sharing ' + ('configured. Restart ORC to use it.' if args.action == 'enable' else 'disabled.'))


if __name__ == '__main__':
    main()
