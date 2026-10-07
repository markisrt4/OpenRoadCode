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


def test_resume_queues_animation_without_drawing_inside_button_callback():
    panel = SimpleNamespace(
        _animation_enabled=False, _animation_job=None,
        _paint_animation_status=Mock(), _queue_engine_animation=Mock(),
        _schedule_engine_animation=Mock(), after_cancel=Mock(),
    )
    EcuPanel.set_engine_animation(panel, True)
    assert panel._animation_enabled
    panel._queue_engine_animation.assert_called_once_with()
    panel._schedule_engine_animation.assert_not_called()
    EcuPanel.set_engine_animation(panel, True)
    panel._queue_engine_animation.assert_called_once_with()


def test_pause_cancels_timer_and_resume_can_queue_again():
    panel = SimpleNamespace(
        _animation_enabled=True, _animation_job='pending',
        _paint_animation_status=Mock(), _queue_engine_animation=Mock(),
        after_cancel=Mock(),
    )
    EcuPanel.set_engine_animation(panel, False)
    panel.after_cancel.assert_called_once_with('pending')
    assert panel._animation_job is None
    EcuPanel.set_engine_animation(panel, True)
    assert panel._animation_enabled
    panel._queue_engine_animation.assert_called_once_with()
