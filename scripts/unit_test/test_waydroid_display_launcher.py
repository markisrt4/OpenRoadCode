# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import json
import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'development/debian/start_waydroid_display.sh'
pytestmark = pytest.mark.skipif(os.geteuid() == 0, reason='launcher requires a desktop user')


@pytest.mark.parametrize('exit_code', [0, 3])
def test_kiosk_marker_is_cleaned_even_after_startup_failure(tmp_path, exit_code):
    executable = tmp_path / 'weston'
    executable.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ['ORC_TEST_KIOSK_ARGS']).write_text(json.dumps(sys.argv[1:]))
sys.exit(int(os.environ['ORC_TEST_KIOSK_EXIT']))
''')
    executable.chmod(0o755)
    record = tmp_path / 'arguments.json'
    env = dict(os.environ, DISPLAY=':93', XDG_RUNTIME_DIR=str(tmp_path),
               PATH=str(tmp_path) + os.pathsep + os.environ['PATH'],
               ORC_TEST_KIOSK_ARGS=str(record), ORC_TEST_KIOSK_EXIT=str(exit_code))
    result = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode == exit_code
    assert '--shell=kiosk-shell.so' in json.loads(record.read_text())
    assert not (tmp_path / 'openroadcode-waydroid-kiosk').exists()


def test_launcher_refuses_an_existing_compositor_socket(tmp_path):
    (tmp_path / 'wayland-0').touch()
    env = dict(os.environ, DISPLAY=':93', XDG_RUNTIME_DIR=str(tmp_path))
    result = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode != 0
    assert 'socket is in use' in result.stderr
