"""Real geometry and lifecycle checks for drawers beside native viewer hosts."""
import os
import tkinter as tk
from dataclasses import replace
from unittest.mock import Mock

import pytest

from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.navigation_experience_controls import NavigationExperienceControls
from ui.navigation.navigation_experience_if import NavigationExperience, NavigationExperienceState, NavigationPlacesDrawerState
from ui.navigation.poi_models import PoiCategory, PointOfInterest
from ui.navigation import GeoPoint
from ui.theme import ThemeMode


@pytest.fixture
def layout():
    if not os.environ.get('DISPLAY'):
        pytest.skip('real X11 display required')
    root = tk.Tk()
    root.geometry('1000x600')
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)
    viewer = tk.Frame(root)
    viewer.grid(row=1, column=0, sticky='nsew')
    handler = Mock(state=NavigationExperienceState(terrain_available=True, waze_available=True))
    bar = NavigationExperienceControls(root, drawer_parent=root, drawer_row=1, drawer_column=1,
        handler=handler, theme=theme_bundle(ThemeMode.DARK))
    bar.grid(row=0, column=0, columnspan=2, sticky='ew')
    root.update()
    yield root, viewer, bar, handler
    root.destroy()


def test_drawer_reduces_viewport_and_restores_it_without_overlap(layout):
    root, viewer, bar, _ = layout
    full_width = viewer.winfo_width()
    bar.show_drawer('views')
    root.update()
    assert viewer.winfo_width() < full_width
    assert viewer.winfo_rootx() + viewer.winfo_width() <= bar._drawer.winfo_rootx()
    assert bar._cards[NavigationExperience.WAZE].winfo_ismapped()
    bar.show_drawer('places')
    root.update()
    assert not bar._views.winfo_ismapped()
    assert bar._places.winfo_ismapped()
    bar.close_drawer()
    root.update()
    assert viewer.winfo_width() == full_width


def test_selection_closes_drawer_and_results_emit_semantic_requests(layout):
    root, _, bar, handler = layout
    bar.show_drawer('views')
    bar._cards[NavigationExperience.WAZE].invoke()
    handler.request_experience.assert_called_once_with(NavigationExperience.WAZE)
    assert bar._drawer_kind is None
    place = PointOfInterest('1', 'Panera Bread', PoiCategory.FOOD, GeoPoint(.7, -1.4))
    bar.set_places_state(NavigationPlacesDrawerState((place,), '1 result'))
    bar.show_drawer('places')
    root.update()
    bar._results.winfo_children()[0].invoke()
    handler.request_select_place.assert_called_once_with(place)


def test_destroy_cancels_poll_and_releases_sibling_drawer(layout):
    root, _, bar, _ = layout
    bar.show_drawer('views')
    drawer = str(bar._drawer)
    job = bar._poll_job
    bar.destroy()
    root.update()
    assert not root.tk.call('winfo', 'exists', drawer)
    assert job not in root.tk.call('after', 'info')


def test_unavailable_and_busy_states_disable_cards_and_show_running_session(layout):
    _, _, bar, handler = layout
    handler.state = replace(handler.state, waze_running=True, terrain_available=False)
    bar.after_cancel(bar._poll_job)
    bar._poll()
    assert 'Resume' in bar._cards[NavigationExperience.WAZE].cget('text')
    assert bar._cards[NavigationExperience.TERRAIN].cget('state') == 'disabled'
    handler.state = replace(handler.state, busy=True)
    bar.after_cancel(bar._poll_job)
    bar._poll()
    assert all(button.cget('state') == 'disabled' for button in bar._cards.values())


def test_compact_layout_keeps_toolbar_and_drawer_close_reachable(layout):
    root, viewer, bar, _ = layout
    root.geometry('522x240')
    root.update()
    bar.show_drawer('views')
    root.update()
    assert viewer.winfo_width() >= 200
    assert bar.views_button.winfo_ismapped()
    assert bar.places_button.winfo_rootx() + bar.places_button.winfo_width() <= bar.views_button.winfo_rootx()
    assert bar._drawer.winfo_rootx() + bar._drawer.winfo_width() <= root.winfo_rootx() + root.winfo_width()
    assert bar._canvas.bbox('all')[3] > bar._canvas.winfo_height()


def test_theme_change_keeps_drawer_and_selection_without_relaunch_requests(layout):
    root, _, bar, handler = layout
    bar.show_drawer('views')
    bar.set_theme(theme_bundle(ThemeMode.LIGHT))
    root.update()
    assert bar._drawer_kind == 'views'
    assert bar.views_button.cget('bg') == theme_bundle(ThemeMode.LIGHT).ui.control_background
    handler.request_experience.assert_not_called()


def test_loading_label_covers_launch_and_native_attachment_then_disappears(layout):
    root, _, bar, handler = layout
    handler.state = replace(handler.state, waze_loading=True, busy=True)
    bar.after_cancel(bar._poll_job)
    bar._poll()
    root.update()
    assert bar._loading_label.winfo_ismapped()
    assert bar._loading_label.cget('text') == 'Loading Waze…'
    bar.set_surface_loading(True)
    handler.state = replace(handler.state, waze_loading=False, busy=False)
    bar.after_cancel(bar._poll_job)
    bar._poll()
    root.update()
    assert bar._loading_label.winfo_ismapped()
    bar.set_surface_loading(False)
    root.update()
    assert not bar._loading_label.winfo_ismapped()
    handler.request_experience.assert_not_called()
