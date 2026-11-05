# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Target one explicitly configured Waydroid ADB device; no runtime sudo."""
import json
import math
import os
from pathlib import Path
import subprocess

from ui.navigation.location_sharing_if import AndroidLocationProviderIf


def configuration_path():
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'openroadcode/waydroid-location.json'


class WaydroidLocationProvider(AndroidLocationProviderIf):
    def __init__(self, serial):
        if not isinstance(serial, str) or not serial or serial.startswith('-') or any(c.isspace() for c in serial):
            raise ValueError('Invalid Waydroid ADB device')
        self._serial = serial
        self._owns_provider = False

    @classmethod
    def from_config(cls):
        try:
            value = json.loads(configuration_path().read_text())
            return cls(value['serial']) if value.get('enabled') is True else None
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _command(self, *arguments):
        try:
            result = subprocess.run(['adb', '-s', self._serial, 'shell', 'cmd', 'location', *arguments],
                capture_output=True, text=True, timeout=3, check=False)
        except (OSError, subprocess.SubprocessError) as error:
            raise RuntimeError('Android location connection failed') from error
        output = result.stdout + result.stderr
        if result.returncode != 0 or any(label in output for label in ('Exception', 'Error:', 'Unknown command')):
            raise RuntimeError('Android location provider rejected the request')

    def send_location(self, point, accuracy_m):
        if not self._owns_provider:
            try:
                model = subprocess.run(['adb', '-s', self._serial, 'shell', 'getprop', 'ro.product.model'],
                                       capture_output=True, text=True, timeout=3, check=True)
            except (OSError, subprocess.SubprocessError) as error:
                raise RuntimeError('The configured Waydroid device is not connected') from error
            if 'waydroid' not in model.stdout.casefold():
                raise RuntimeError('The configured Android device is not Waydroid')
            self._command('providers', 'add-test-provider', 'gps', '--requiresSatellite', '--accuracy', '1')
            self._owns_provider = True
            self._command('providers', 'set-test-provider-enabled', 'gps', 'true')
        self._command('providers', 'set-test-provider-location', 'gps', '--location',
                      f'{math.degrees(point.latitude_rad):.8f},{math.degrees(point.longitude_rad):.8f}',
                      '--accuracy', str(accuracy_m))

    def clear_location(self):
        if self._owns_provider:
            try:
                self._command('providers', 'remove-test-provider', 'gps')
            finally:
                # A disconnected/restarted Android may already have lost the
                # provider. Revalidate the device and recreate it on retry.
                self._owns_provider = False
