# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Retired widgets must release Tcl resources before worker-thread collection."""
import gc
import os
from threading import Thread, get_ident
import tkinter as tk
from unittest.mock import Mock

import pytest

from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
from apps.orcUi.frontend.tk.navigation_route_weather import NavigationRouteWeather
from apps.orcUi.theme_runtime import theme_bundle
from controllers.navigation.map_controls_drawer_controller import MapControlsDrawerController
from ui.navigation import MapRequestHandlerStub
from ui.navigation.navigation_experience_if import NavigationExperienceState
from ui.navigation.navigation_places_request_handler_if import NavigationPlacesRequestHandlerIf
from ui.theme import ThemeMode


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Tk resources need X11')
@pytest.mark.parametrize('root_first', [False, True])
def test_destroy_releases_navigation_variables_and_preview_images_on_ui_thread(monkeypatch, root_first):
    gc.collect()
    ui_thread = get_ident()
    finalized = {}
    # Record finalization affinity without deliberately calling Tcl on a worker
    # in the failing case (which can otherwise abort the entire test process).
    for resource_type in (tk.Variable, tk.Image):
        original = resource_type.__del__

        def finalize(resource, original=original):
            finalized[id(resource)] = get_ident()
            if get_ident() == ui_thread:
                original(resource)

        monkeypatch.setattr(resource_type, '__del__', finalize)
    root = tk.Tk()
    root.geometry('1000x600')
    places = Mock(spec=NavigationPlacesRequestHandlerIf)
    places.poll_search_result.return_value = None
    places.poll_selected.return_value = None
    places.poll_camera_interaction.return_value = False
    drawer = MapControlsDrawerController()
    panel = NavigationPanel(root, map_request_handler=MapRequestHandlerStub(), places_handler=places,
        drawer_handler=drawer, experience_handler=Mock(state=NavigationExperienceState()),
        theme_bundle=theme_bundle(ThemeMode.DARK), on_radar_toggle=Mock())
    panel.pack(fill=tk.BOTH, expand=True)
    drawer.set_ui(panel)
    root.update()
    weather = NavigationRouteWeather(Mock(), lambda: theme_bundle(ThemeMode.DARK), lambda: Mock(value='imperial'))
    weather.attach(panel)
    weather._toggle_popup()
    root.update()
    resources = {id(value) for value in vars(panel).values() if isinstance(value, tk.Variable)}
    resources.update(id(value) for value in panel._experience_controls._previews.values())
    resources.update(id(value) for value in vars(weather).values() if isinstance(value, tk.Variable))
    resources.update(id(value) for value in weather._layer_vars.values())
    try:
        if root_first:
            root.destroy()
        weather.close()
        panel.destroy()
        drawer.set_ui(None)
        retired = [panel, weather]
        panel = weather = None

        def collect_on_worker():
            retired.clear()
            gc.collect()

        worker = Thread(target=collect_on_worker)
        worker.start()
        worker.join(timeout=3)
        assert not worker.is_alive()
        assert resources <= finalized.keys()
        assert all(finalized[identity] == ui_thread for identity in resources)
    finally:
        if not root_first:
            root.destroy()
