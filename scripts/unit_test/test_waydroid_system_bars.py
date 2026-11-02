# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Exercise the admin helper against a fake Android settings store, never sudo."""
import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'development/debian/waydroid_system_bars.sh'
pytestmark = pytest.mark.skipif(os.geteuid() == 0, reason='helper deliberately requires a normal desktop user')


@pytest.fixture
def settings(tmp_path):
    executable = tmp_path / 'sudo'
    executable.write_text('''#!/usr/bin/env python3
import os, sys
from pathlib import Path
assert sys.argv[1:5] == ['waydroid', 'shell', '--', 'settings']
assert sys.argv[6:8] == ['global', 'policy_control']
store = Path(os.environ['ORC_TEST_BAR_POLICY'])
action = sys.argv[5]
if action == 'get': print(store.read_text() if store.exists() else 'null')
elif action == 'put': store.write_text(sys.argv[8])
elif action == 'delete': store.unlink(missing_ok=True)
else: raise AssertionError(action)
''')
    executable.chmod(0o755)
    policy = tmp_path / 'policy'
    backup = tmp_path / 'state/openroadcode/waydroid-system-bars'
    environment = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ['PATH'],
                       XDG_STATE_HOME=str(tmp_path / 'state'), ORC_TEST_BAR_POLICY=str(policy))
    def run(*arguments):
        return subprocess.run(['bash', str(SCRIPT), *arguments], env=environment,
                              capture_output=True, text=True, timeout=5)
    return policy, backup, run


def test_hide_restore_and_repeated_hide_preserves_original(settings):
    policy, backup, run = settings
    assert run('hide', 'com.panera.bread').returncode == 0
    original = backup.read_text()
    assert policy.read_text() == 'immersive.full=com.panera.bread'
    assert run('hide', 'com.other.app').returncode != 0
    assert backup.read_text() == original
    assert run('restore').returncode == 0
    assert not backup.exists()
    assert not policy.exists()


def test_existing_or_changed_policy_is_not_overwritten(settings):
    policy, backup, run = settings
    policy.write_text('immersive.status=com.other.app')
    assert run('hide', 'com.panera.bread').returncode != 0
    assert not backup.exists()
    policy.unlink()
    assert run('hide', 'com.panera.bread').returncode == 0
    policy.write_text('immersive.full=com.other.app')
    assert run('restore').returncode != 0
    assert policy.read_text() == 'immersive.full=com.other.app'
    assert backup.exists()
