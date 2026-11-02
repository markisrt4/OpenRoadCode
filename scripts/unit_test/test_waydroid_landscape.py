# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import json

import pytest

from scripts import waydroid_landscape as landscape


def queries(size='Physical size: 1280x720'):
    return {('wm', 'user-rotation'): 'free',
            ('wm', 'fixed-to-user-rotation'): 'default',
            ('wm', 'get-ignore-orientation-request'): 'ignoreOrientationRequest false for displayId=0',
            ('settings', 'get', 'global', 'force_resizable_activities'): 'null',
            ('wm', 'size'): size}


@pytest.mark.parametrize(('size', 'rotation'), [('Physical size: 1280x720', '0'), ('Physical size: 720x1280', '1')])
def test_apply_saves_original_and_uses_natural_landscape(monkeypatch, tmp_path, size, rotation):
    calls = []
    def android(*arguments):
        calls.append(arguments)
        return queries(size).get(arguments, '')
    monkeypatch.setattr(landscape, 'android', android)
    backup = tmp_path / 'backup.json'
    landscape.apply(backup)
    assert json.loads(backup.read_text())['rotation'] == 'free'
    assert ('wm', 'user-rotation', 'lock', rotation) in calls
    assert ('wm', 'set-ignore-orientation-request', 'true') in calls
    with pytest.raises(ValueError, match='already saved'):
        landscape.apply(backup)
    calls.clear()
    landscape.restore(backup)
    assert ('wm', 'user-rotation', 'free') in calls
    assert ('wm', 'fixed-to-user-rotation', 'default') in calls
    assert ('wm', 'set-ignore-orientation-request', 'false') in calls
    assert ('settings', 'delete', 'global', 'force_resizable_activities') in calls
    assert not backup.exists()


def test_partial_failure_keeps_original_for_restore(monkeypatch, tmp_path):
    def android(*arguments):
        if arguments == ('wm', 'fixed-to-user-rotation', 'enabled'):
            raise OSError('failed')
        return queries().get(arguments, '')
    monkeypatch.setattr(landscape, 'android', android)
    backup = tmp_path / 'backup.json'
    with pytest.raises(OSError):
        landscape.apply(backup)
    assert json.loads(backup.read_text())['fixed'] == 'default'


def test_unrecognized_platform_does_not_write_settings(monkeypatch, tmp_path):
    calls = []
    def android(*arguments):
        calls.append(arguments)
        return 'unsupported'
    monkeypatch.setattr(landscape, 'android', android)
    with pytest.raises(ValueError):
        landscape.apply(tmp_path / 'backup.json')
    assert not any('put' in call or 'lock' in call for call in calls)
