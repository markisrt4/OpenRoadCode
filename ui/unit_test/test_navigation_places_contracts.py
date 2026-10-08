# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Incomplete bindings are rejected and screen lifecycle releases places sessions."""
from unittest.mock import Mock
import pytest
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
from ui.navigation.navigation_places_request_handler_if import NavigationPlacesFactoryIf, NavigationPlacesRequestHandlerIf


def make_screen(factory):
    return NavigationScreen(Mock(), places_factory=factory, map_runtime=Mock(),
                            map_request_handler=Mock(), route_request_handler=Mock(),
                            route_simulation_handler=Mock(), theme_bundle=Mock(),
                            telemetry_profile_request=None, on_back=Mock())


def test_invalid_factory_and_incomplete_handler_are_rejected():
    with pytest.raises(TypeError, match='NavigationPlacesFactoryIf'):
        make_screen(object())
    with pytest.raises(TypeError):
        NavigationPlacesRequestHandlerIf()


def test_hide_and_close_release_session_once():
    screen = make_screen(Mock(spec=NavigationPlacesFactoryIf))
    session = Mock(spec=NavigationPlacesRequestHandlerIf)
    screen._places_session = session
    panel = Mock()
    screen._panel = panel
    screen.hide()
    screen.close()
    session.close.assert_called_once_with()
    panel.close_places.assert_called_once_with()
    screen._map_runtime.stop.assert_called_once_with()


def test_invalid_panel_binding_fails_before_tk_initialization():
    from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
    with pytest.raises(TypeError, match='NavigationPlacesRequestHandlerIf'):
        NavigationPanel(Mock(), map_request_handler=Mock(), places_handler=object())


def test_invalid_factory_result_is_rejected_before_panel_construction():
    factory = Mock(spec=NavigationPlacesFactoryIf)
    factory.create.return_value = object()
    screen = make_screen(factory)
    with pytest.raises(TypeError, match='NavigationPlacesRequestHandlerIf'):
        screen.show()
    assert screen._places_session is None


def test_failed_panel_construction_closes_session():
    from unittest.mock import patch
    factory = Mock(spec=NavigationPlacesFactoryIf)
    factory.create.return_value = Mock(spec=NavigationPlacesRequestHandlerIf)
    screen = make_screen(factory)
    with patch('apps.orcUi.frontend.tk.navigation_screen.build_navigation_screen',
               side_effect=RuntimeError('widget failed')):
        with pytest.raises(RuntimeError, match='widget failed'):
            screen.show()
    factory.create.return_value.close.assert_called_once_with()
    assert screen._places_session is None
