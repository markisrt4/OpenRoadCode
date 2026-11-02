#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Explicit, reversible Android 13 landscape experiment for a dedicated Linux VM."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def android(*arguments: str) -> str:
    result = subprocess.run(['sudo', 'waydroid', 'shell', '--', *arguments],
                            capture_output=True, text=True, timeout=20, check=True)
    return result.stdout.replace('\r', '').strip()


def snapshot() -> dict:
    rotation = android('wm', 'user-rotation')
    fixed = android('wm', 'fixed-to-user-rotation')
    ignore = android('wm', 'get-ignore-orientation-request')
    resizable = android('settings', 'get', 'global', 'force_resizable_activities')
    size = android('wm', 'size')
    if not re.fullmatch(r'free|lock [0-3]', rotation):
        raise ValueError('Could not read Android rotation mode; no settings were changed.')
    if fixed not in {'enabled', 'disabled', 'default'}:
        raise ValueError('Could not read Android fixed rotation mode; no settings were changed.')
    ignore_match = re.fullmatch(r'ignoreOrientationRequest (true|false) for displayId=0', ignore)
    sizes = re.findall(r'(?:Physical|Override) size:\s*(\d+)x(\d+)', size)
    if ignore_match is None or not sizes or resizable not in {'null', '0', '1'}:
        raise ValueError('Android display settings were not recognized; no settings were changed.')
    width, height = map(int, sizes[-1])
    return {'version': 1, 'rotation': rotation, 'fixed': fixed,
            'ignore': ignore_match[1], 'resizable': resizable,
            # A nested Waydroid display normally has natural landscape at 0.
            'landscape_rotation': '0' if width >= height else '1'}


def apply(backup: Path) -> None:
    if backup.exists():
        raise ValueError('A landscape experiment is already saved. Restore it before applying again.')
    saved = snapshot()
    backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(saved, stream)
    # Save before mutating so partial failures can also be restored.
    android('settings', 'put', 'global', 'force_resizable_activities', '1')
    android('wm', 'fixed-to-user-rotation', 'enabled')
    android('wm', 'user-rotation', 'lock', saved['landscape_rotation'])
    android('wm', 'set-ignore-orientation-request', 'true')


def restore(backup: Path) -> None:
    saved = json.loads(backup.read_text())
    if (not isinstance(saved, dict) or saved.get('version') != 1
            or not re.fullmatch(r'free|lock [0-3]', saved.get('rotation', ''))
            or saved.get('fixed') not in {'enabled', 'disabled', 'default'}
            or saved.get('ignore') not in {'true', 'false'}
            or saved.get('resizable') not in {'null', '0', '1'}):
        raise ValueError('Saved display settings are not recognized; no settings were changed.')
    android('wm', 'set-ignore-orientation-request', saved['ignore'])
    android('wm', 'fixed-to-user-rotation', saved['fixed'])
    android('wm', 'user-rotation', *saved['rotation'].split())
    if saved['resizable'] == 'null':
        android('settings', 'delete', 'global', 'force_resizable_activities')
    else:
        android('settings', 'put', 'global', 'force_resizable_activities', saved['resizable'])
    backup.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('apply', 'restore'))
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as your normal desktop user; individual Android commands use sudo.')
    state_root = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state')))
    backup = state_root / 'openroadcode/waydroid-landscape.json'
    try:
        if args.action == 'apply':
            apply(backup)
            print('Landscape experiment applied to Android display 0. Close and reopen Panera.')
            print('This affects the entire VM Android display; app compatibility still needs testing.')
        else:
            restore(backup)
            print('Previous Android display settings restored. Close and reopen the Android app.')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Landscape experiment failed: {error}')
        if backup.exists():
            print('Saved settings remain available; use restore if any changes were applied.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
