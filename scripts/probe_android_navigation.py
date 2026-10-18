#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only host facts for the native-Android/Waydroid Waze investigation.

Does not launch apps, start an ADB server/container, pair a device, install
packages or change system settings. Does not collect GPS fixes or device IDs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess


def query(arguments: list[str]) -> tuple[int | None, str]:
    try:
        result = subprocess.run(arguments, capture_output=True, text=True,
                                check=False, timeout=4)
        return result.returncode, result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None, ''


def waydroid_facts() -> dict:
    if shutil.which('waydroid') is None:
        return {'installed': False, 'runtime': 'not checked'}
    code, output = query(['waydroid', 'status'])
    if code != 0:
        return {'installed': True, 'runtime': 'query failed or unavailable'}
    # Do not include the IP or arbitrary log output in a shared report.
    status = {}
    for label in ('Session', 'Container'):
        match = re.search(r'^\s*' + label + r':\s*(RUNNING|STOPPED|FROZEN)\s*$',
                          output, re.MULTILINE | re.IGNORECASE)
        status[label.lower()] = match.group(1).upper() if match else 'unknown'
    result = {'installed': True, **status, 'waze_package': 'not checked'}
    if status['session'] == 'RUNNING' and status['container'] == 'RUNNING':
        code, apps = query(['waydroid', 'app', 'list'])
        if code == 0:
            result['waze_package'] = bool(re.search(r'^\s*packageName:\s*com\.waze\s*$',
                                                   apps, re.MULTILINE))
    return result


def collect() -> dict:
    android = Path('/system/bin/getprop').exists()
    result = {
        'host': {'system': platform.system(), 'kernel': platform.release(),
                 'architecture': platform.machine(), 'page_size_bytes': os.sysconf('SC_PAGE_SIZE'),
                 'android_host_visible': android},
        'display': {'x11_environment': bool(os.getenv('DISPLAY')),
                    'wayland_environment': bool(os.getenv('WAYLAND_DISPLAY'))},
        'tools': {name: shutil.which(name) is not None for name in
                  ('waydroid', 'weston', 'adb', 'scrcpy', 'termux-open-url', 'xdotool')},
        'binder': {name: Path(name).exists() for name in
                   ('/sys/module/binder_linux', '/dev/binderfs', '/dev/binder')},
        'waydroid': waydroid_facts(),
    }
    if android:
        result['android'] = {}
        for label, prop in (('sdk', 'ro.build.version.sdk'), ('abi', 'ro.product.cpu.abi')):
            code, value = query(['/system/bin/getprop', prop])
            result['android'][label] = value.strip()[:80] if code == 0 else 'unknown'
        code, output = query(['/system/bin/pm', 'path', 'com.waze'])
        result['android']['waze_package'] = (
            True if code == 0 and output.strip().startswith('package:')
            else 'unknown: package query unavailable or not visible'
        )
    if result['tools']['scrcpy']:
        code, output = query(['scrcpy', '--version'])
        result['scrcpy_version'] = output.splitlines()[0][:120] if code == 0 and output else 'unknown'
        code, output = query(['scrcpy', '--help'])
        result['scrcpy_options'] = {flag: flag in output if code == 0 else None for flag in
                                  ('--new-display', '--start-app', '--display-ime-policy')}
    return result


if __name__ == '__main__':
    print(json.dumps(collect(), indent=2))
