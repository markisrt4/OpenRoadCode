# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Optional perception setup must not prevent the cockpit from starting."""

from unittest.mock import Mock, patch

import pytest

from apps.orcUi.composition.vision import configure_vision
from ui.vision.vision_ui_state import VisionLifecycle


@pytest.mark.parametrize('error', [
    RuntimeError('Ultralytics is required for VISION'),
    ModuleNotFoundError('torch missing'),
    OSError('model weights unavailable'),
])
def test_unavailable_model_registers_error_screen_without_starting_resources(error):
    app = Mock()
    with patch('apps.orcUi.composition.vision.YoloModelReadiness') as readiness, \
            patch('apps.orcUi.composition.vision.CameraVisionScreen') as screen, \
            patch('apps.orcUi.composition.vision.VisionController') as controller, \
            patch('apps.orcUi.composition.vision.V4L2Camera') as camera:
        readiness.return_value.prepare.side_effect = error
        composition = configure_vision(app)
        state = screen.return_value.set_vision_state.call_args.args[0]
        assert state.lifecycle is VisionLifecycle.ERROR
        assert not state.ai_enabled
        assert str(error) in state.status_message
        app.register_screen.assert_called_once_with('VISION', screen.return_value, before='CONTROLS')
        controller.assert_not_called()
        camera.assert_not_called()
        assert composition.controller is None
        composition.close()
        composition.close()


def test_ready_model_keeps_existing_vision_controller_lifecycle():
    app = Mock()
    with patch('apps.orcUi.composition.vision.YoloModelReadiness') as readiness, \
            patch('apps.orcUi.composition.vision.CameraVisionScreen') as screen, \
            patch('apps.orcUi.composition.vision.VisionController') as controller, \
            patch('apps.orcUi.composition.vision.YoloObjectDetector') as detector, \
            patch('apps.orcUi.composition.vision.ByteTrackObjectTracker'):
        composition = configure_vision(app)
        assert detector.call_args.kwargs['model'] is readiness.return_value.prepare.return_value
        assert composition.controller is controller.return_value
        screen.return_value.set_vision_state.assert_not_called()
        composition.close()
        controller.return_value.close.assert_called_once_with()


def test_missing_tracking_dependency_also_keeps_cockpit_available():
    with patch('apps.orcUi.composition.vision.YoloModelReadiness'), \
            patch('apps.orcUi.composition.vision.CameraVisionScreen') as screen, \
            patch('apps.orcUi.composition.vision.YoloObjectDetector'), \
            patch('apps.orcUi.composition.vision.ByteTrackObjectTracker') as tracker, \
            patch('apps.orcUi.composition.vision.VisionController') as controller:
        tracker.side_effect = RuntimeError('supervision missing')
        composition = configure_vision(Mock())
        assert composition.controller is None
        controller.assert_not_called()
        assert 'supervision missing' in screen.return_value.set_vision_state.call_args.args[0].status_message
        composition.close()
