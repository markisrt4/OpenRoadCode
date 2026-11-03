# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import patch
import pytest

from apps.orcUi.composition.application import _android_panel_backends


@pytest.mark.parametrize('android,tools,expected', [
    (False, {'waydroid'}, (True, False)),
    (False, set(), (False, False)),
    (True, {'adb', 'scrcpy'}, (False, True)),
    (True, {'adb'}, (False, False)),
    (True, {'waydroid'}, (False, False)),
])
def test_installed_native_backend_is_selected_without_manual_flags(android, tools, expected, monkeypatch):
    monkeypatch.delenv('ORC_WAYDROID_PANEL', raising=False)
    monkeypatch.delenv('ORC_SCRCPY_WAZE', raising=False)
    with patch('apps.orcUi.composition.application.os.path.exists', return_value=android), \
            patch('apps.orcUi.composition.application.shutil.which',
                  side_effect=lambda name: '/usr/bin/' + name if name in tools else None):
        assert _android_panel_backends() == expected


@pytest.mark.parametrize('android,flag', [(False, 'ORC_WAYDROID_PANEL'), (True, 'ORC_SCRCPY_WAZE')])
def test_explicit_opt_out_is_respected(android, flag, monkeypatch):
    monkeypatch.setenv(flag, '0')
    with patch('apps.orcUi.composition.application.os.path.exists', return_value=android), \
            patch('apps.orcUi.composition.application.shutil.which', return_value='/usr/bin/tool'):
        assert _android_panel_backends() == (False, False)
