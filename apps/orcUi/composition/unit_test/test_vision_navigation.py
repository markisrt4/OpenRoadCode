# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Check frame observation, lazy bus ownership and stale ingress completions."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from apps.orcUi.adapters.vision_navigation import VisionNavigationIngress, VisionNavigationUiAdapter
from apps.orcUi.composition.vision import VisionComposition
from ui.vision.vision_ui_state import VisionImage, VisionPixelFormat, VisionUiState


def test_image_is_presented_before_new_frame_guidance_can_replace_the_old_hud():
    events = Mock()
    navigation, ui = Mock(), Mock()
    navigation.set_frame.side_effect = events.frame
    ui.set_vision_state.side_effect = events.vision
    adapter = VisionNavigationUiAdapter(ui, navigation)
    image = VisionImage(2, 1, 6, VisionPixelFormat.RGB888, 10, 1, b'\0' * 6)
    state = VisionUiState(image=image)
    adapter.set_vision_state(state)
    assert events.mock_calls[0].args == (state,)
    assert events.mock_calls[1].args == (10,)
    adapter.set_vision_state(VisionUiState())
    navigation.set_frame.assert_called_with(None)
    handler = Mock()
    adapter.set_vision_request_handler(handler)
    ui.set_vision_request_handler.assert_called_once_with(handler)


def test_ingress_is_lazy_ordered_and_closed_once():
    navigation = Mock()
    with patch('apps.orcUi.adapters.vision_navigation.ZeroMqSubscriber') as subscriber, \
            patch('apps.orcUi.adapters.vision_navigation.MessageDispatcher') as dispatcher:
        ingress = VisionNavigationIngress(navigation)
        subscriber.assert_not_called()
        ingress.start()
        ingress.start()
        assert dispatcher.call_args.kwargs['max_workers'] == 1
        assert dispatcher.return_value.register.call_count == 3
        dispatcher.return_value.start.assert_called_once()
        ingress.close()
        ingress.close()
        dispatcher.return_value.close.assert_called_once()
        ingress.start()
        assert subscriber.call_count == 1


def test_duplicate_positions_do_not_refresh_gps_age_and_closed_handlers_are_inert():
    navigation = Mock()
    ingress = VisionNavigationIngress(navigation)
    data = SimpleNamespace(fix_mode=3, latitude_rad=1, longitude_rad=1,
                           is_cached=False, accuracy_m=3)
    message = SimpleNamespace(timestamp=SimpleNamespace(seconds=10, nanoseconds=0), data=data)
    ingress._on_position(message)
    ingress._on_position(message)
    navigation.update_position.assert_called_once()
    ingress.close()
    navigation.reset_mock()
    message.timestamp.seconds = 11
    ingress._on_position(message)
    ingress._on_motion(message)
    ingress._on_guidance(message)
    assert navigation.mock_calls == []


def test_start_does_not_open_camera_or_prepare_ai_and_cleanup_attempts_all_resources():
    screen, vision, readiness, navigation, ingress = (Mock() for _ in range(5))
    composition = VisionComposition(screen, vision, readiness, navigation, ingress)
    composition.start()
    ingress.start.assert_called_once()
    readiness.prepare.assert_not_called()
    assert vision.mock_calls == []
    composition.close()
    ingress.close.assert_called_once()
    navigation.close.assert_called_once()
    vision.close.assert_called_once()
