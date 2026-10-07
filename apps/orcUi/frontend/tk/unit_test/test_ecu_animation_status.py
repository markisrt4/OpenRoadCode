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
                            _animation_toggle=button,
                            _visual_analysis=lambda: SimpleNamespace(engine_running=running))
    EcuPanel._paint_animation_status(panel)
    button.configure.assert_called_once_with(text=f'Animation: {expected}')


@pytest.mark.parametrize(('rpm', 'analysis', 'expected'), [
    (900.0, None, True), (900.0, False, True), (0.0, True, False),
    (None, True, True), (None, None, None), (float('nan'), False, False),
])
def test_live_rpm_controls_motion_even_when_analysis_lags(rpm, analysis, expected):
    from apps.orcUi.frontend.tk.ecu_panel import visual_engine_running
    assert visual_engine_running(rpm, analysis) is expected


def test_draw_error_does_not_drop_animation_timer():
    panel = SimpleNamespace(
        _animation_job='old', _animation_enabled=True, _animation_time=0,
        _animation_phase=0, _vehicle_state=SimpleNamespace(engine_speed_rpm=900),
        winfo_exists=lambda: True, winfo_ismapped=lambda: True,
        _visual_analysis=lambda: SimpleNamespace(engine_running=True),
        _paint_engine=Mock(side_effect=RuntimeError('draw failed')),
        _queue_engine_animation=Mock(),
    )
    with pytest.raises(RuntimeError, match='draw failed'):
        EcuPanel._schedule_engine_animation(panel)
    assert panel._animation_phase > 0
    panel._queue_engine_animation.assert_called_once_with()
