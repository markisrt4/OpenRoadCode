# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Make waiting for telemetry distinguishable from active animation."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.orcUi.frontend.tk.ecu_panel import EcuPanel


@pytest.mark.parametrize(('enabled', 'running', 'expected'), [
    (True, True, 'On'),
    (True, False, 'Engine off'),
    (True, None, 'Waiting for RPM'),
    (False, True, 'Off'),
    (False, None, 'Off'),
])
def test_animation_status_explains_why_motion_is_stopped(enabled, running, expected):
    button = Mock()
    panel = SimpleNamespace(_animation_enabled=enabled,
                            _analysis=SimpleNamespace(engine_running=running),
                            _animation_toggle=button)
    EcuPanel._paint_animation_status(panel)
    button.configure.assert_called_once_with(text=f'Animation: {expected}')
