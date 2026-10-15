# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Optional perception setup must not prevent the cockpit from starting."""

from unittest.mock import Mock, patch

from apps.orcUi.composition.vision import configure_vision


def test_model_loading_is_deferred_until_vision_activation():
    app = Mock()
    with patch('apps.orcUi.composition.vision.YoloModelReadiness') as readiness, \
            patch('apps.orcUi.composition.vision.CameraVisionScreen') as screen, \
            patch('apps.orcUi.composition.vision.VisionController') as controller, \
            patch('apps.orcUi.composition.vision.LazyYoloObjectDetector') as detector, \
            patch('apps.orcUi.composition.vision.ByteTrackObjectTracker'):
        composition = configure_vision(app)

        readiness.return_value.prepare.assert_not_called()
        assert controller.call_args.kwargs['prepare_model'] is detector.return_value.prepare
        app.register_screen.assert_called_once_with('VISION', screen.return_value, before='CONTROLS')
        assert composition.controller is controller.return_value
        composition.close()


def test_ready_model_keeps_existing_vision_controller_lifecycle():
    app = Mock()
    with patch('apps.orcUi.composition.vision.YoloModelReadiness') as readiness, \
            patch('apps.orcUi.composition.vision.CameraVisionScreen') as screen, \
            patch('apps.orcUi.composition.vision.VisionController') as controller, \
            patch('apps.orcUi.composition.vision.LazyYoloObjectDetector') as detector, \
            patch('apps.orcUi.composition.vision.ByteTrackObjectTracker'):
        composition = configure_vision(app)
        detector.assert_called_once_with(readiness.return_value, confidence=0.10, image_size=640)
        readiness.return_value.prepare.assert_not_called()
        assert composition.controller is controller.return_value
        screen.return_value.set_vision_state.assert_not_called()
        composition.close()
        controller.return_value.close.assert_called_once_with()


def test_missing_tracking_dependency_keeps_live_camera_and_navigation_available():
    with patch('apps.orcUi.composition.vision.YoloModelReadiness'), \
            patch('apps.orcUi.composition.vision.CameraVisionScreen') as screen, \
            patch('apps.orcUi.composition.vision.LazyYoloObjectDetector'), \
            patch('apps.orcUi.composition.vision.ByteTrackObjectTracker') as tracker, \
            patch('apps.orcUi.composition.vision.VisionController') as controller:
        tracker.side_effect = RuntimeError('supervision missing')
        composition = configure_vision(Mock())
        assert composition.controller is controller.return_value
        assert controller.call_args.args[5] is None
        assert controller.call_args.kwargs['prepare_model'] is None
        assert controller.call_args.kwargs['ai_unavailable_reason'] == 'supervision missing'
        screen.return_value.set_vision_state.assert_not_called()
        composition.close()
