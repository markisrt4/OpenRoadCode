#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only dimensions of ORC's hosted Weston and Android display; no app content."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def query(arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=8, check=False)
        return result.returncode, result.stdout.replace('\r', '').strip()
    except (OSError, subprocess.TimeoutExpired):
        return None, ''


def parse_geometry(output):
    fields = {}
    for key, label in (('width', 'Width'), ('height', 'Height'),
                       ('relative_x', 'Relative upper-left X'), ('relative_y', 'Relative upper-left Y'),
                       ('absolute_x', 'Absolute upper-left X'), ('absolute_y', 'Absolute upper-left Y')):
        match = re.search(r'^\s*' + re.escape(label) + r':\s*(-?\d+)\s*$', output, re.MULTILINE)
        if match:
            fields[key] = int(match[1])
    return fields


def window_geometry(window_id):
    code, output = query(['xwininfo', '-id', str(window_id)])
    return parse_geometry(output) if code == 0 else {'error': 'window unavailable'}


def android_window_frames(output, package='com.panera.bread'):
    """Retain only numeric geometry for the requested app; omit UI/user content."""
    frames, active = [], False
    for line in output.splitlines():
        if re.match(r'^\s*Window #\d+', line):
            active = package in line
        if active and any(label in line for label in ('mFrame=', 'Frames:', 'mBounds=')):
            rectangles = re.findall(r'\[-?\d+[, ]+-?\d+\]\[-?\d+[, ]+-?\d+\]', line)
            if rectangles:
                frames.append(rectangles)
    return frames[:12]


def activity_orientation(output, package='com.panera.bread'):
    """Read only orientation/size-compat metadata from this package's records."""
    records, current, indent = [], None, 0
    for line in output.splitlines():
        header = re.match(r'^(\s*)\* Hist #\d+:.*ActivityRecord\{', line)
        if header:
            if current:
                records.append(current)
            current = {} if package + '/' in line else None
            indent = len(header[1])
            continue
        if current is None:
            continue
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            if current:
                records.append(current)
            current = None
            continue
        for key in ('requestedOrientation', 'overrideOrientation'):
            match = re.search(r'\b' + key + r'=([A-Z_]+|-?\d+)', line)
            if match:
                current[key] = match[1]
        match = re.search(r'\bmSizeCompatScale=([0-9.]+)', line)
        if match:
            current['size_compat_scale'] = match[1]
        if 'mCompatDisplayInsets=' in line:
            current['has_size_compat_insets'] = True
    if current:
        records.append(current)
    return records[:12]


def compatibility_overrides(output, package='com.panera.bread'):
    names = ('FORCE_RESIZE_APP', 'FORCE_NON_RESIZE_APP', 'OVERRIDE_ANY_ORIENTATION',
             'OVERRIDE_UNDEFINED_ORIENTATION_TO_NOSENSOR', 'OVERRIDE_ORIENTATION_ONLY_FOR_CAMERA',
             'OVERRIDE_RESPECT_REQUESTED_ORIENTATION')
    result = {}
    for name in names:
        line = next((line for line in output.splitlines() if 'name=' + name + ';' in line
                     or 'name=' + name + ')' in line), None)
        if line is None:
            result[name] = {'known': False}
            continue
        # Report only the evaluated override, not other packages or raw version rules.
        evaluated = re.search(r'packageOverrides=\{([^}]*)\}', line)
        override = re.search(r'(?<![\w.])' + re.escape(package) + r'=(true|false)\b', evaluated[1]) if evaluated else None
        result[name] = {'known': True, 'default_disabled': '; disabled;' in line or '; disabled)' in line,
                        'panera_override': override[1] == 'true' if override else None}
    return result


def collect(mode):
    report = {'mode': mode, 'x11_display_set': bool(os.getenv('DISPLAY'))}
    code, output = query(['xdotool', 'search', '--class', '^Weston Compositor$'])
    windows = sorted({int(line) for line in output.splitlines() if line.isdigit()}) if code == 0 else []
    report['weston_window_count'] = len(windows)
    if len(windows) == 1:
        report['weston_window'] = window_geometry(windows[0])
        code, tree = query(['xwininfo', '-id', str(windows[0]), '-tree'])
        parent = re.search(r'Parent window id:\s*(0x[0-9a-fA-F]+)', tree) if code == 0 else None
        if parent:
            report['hosting_parent'] = window_geometry(int(parent[1], 16))
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    report['kiosk_marker_present'] = bool(runtime and (Path(runtime) / 'openroadcode-waydroid-kiosk').exists())
    report['waydroid_properties'] = {}
    for key in ('persist.waydroid.width', 'persist.waydroid.height',
                'waydroid.display_width', 'waydroid.display_height', 'persist.waydroid.multi_windows'):
        code, value = query(['waydroid', 'prop', 'get', key])
        report['waydroid_properties'][key] = value[:64] if code == 0 else 'unavailable'
    report['android'] = {}
    for label, arguments in (
            ('size', ['wm', 'size']), ('density', ['wm', 'density']),
            ('rotation', ['wm', 'user-rotation']), ('fixed_rotation', ['wm', 'fixed-to-user-rotation']),
            ('ignore_app_orientation', ['wm', 'get-ignore-orientation-request']),
            ('force_resizable', ['settings', 'get', 'global', 'force_resizable_activities'])):
        code, value = query(['sudo', '-n', 'waydroid', 'shell', '--', *arguments])
        report['android'][label] = value[:256] if code == 0 else 'unavailable (run sudo -v first)'
    code, output = query(['sudo', '-n', 'waydroid', 'shell', '--', 'dumpsys', 'window', 'windows'])
    report['android']['panera_window_rectangles'] = android_window_frames(output) if code == 0 else []
    code, output = query(['sudo', '-n', 'waydroid', 'shell', '--', 'dumpsys', 'activity', 'activities'])
    report['android']['panera_orientation'] = activity_orientation(output) if code == 0 else []
    code, output = query(['sudo', '-n', 'waydroid', 'shell', '--', 'dumpsys', 'platform_compat'])
    report['android']['panera_compat_overrides'] = compatibility_overrides(output) if code == 0 else {'error': 'unavailable'}
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('split', 'expanded'))
    arguments = parser.parse_args()
    print(json.dumps(collect(arguments.mode), indent=2))
