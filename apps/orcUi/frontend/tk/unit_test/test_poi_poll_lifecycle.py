# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import Mock
from types import SimpleNamespace
import tkinter as tk
import pytest

from apps.orcUi.frontend.tk.navigation_places_controls import NavigationPlacesControls
from apps.orcUi.frontend.tk.navigation_panel_layout import show_poi_card
from controllers.poi.poi_enricher import enrich_poi
from ui.navigation import GeoPoint
from ui.navigation.poi_models import PoiAction, PoiActionKind, PoiCategory, PointOfInterest, PoiSearchResult
from controllers.poi.navigation_places_controller import NavigationPlacesController
from ui.theme import ThemeMode
from apps.orcUi.theme_runtime import theme_bundle


def test_ordering_popup_has_one_business_action_through_existing_request_contract():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f'X11 display unavailable: {error}')
    try:
        root.geometry('800x500')
        panel = tk.Frame(root)
        panel.pack(fill=tk.BOTH, expand=True)
        panel._poi_card = None
        panel._theme_bundle = SimpleNamespace(ui=SimpleNamespace(surface_alt='#101820',
            accent_primary='#00aeef', text='#ffffff', text_muted='#aaaaaa',
            control_background='#15212a', control_active='#263848', border='#39464f'))
        panel.online_actions_allowed = True
        panel._refresh_poi_action_buttons = Mock()
        panel._execute_poi_action = Mock()
        panel._add_tooltip = Mock()
        poi = enrich_poi(PointOfInterest('store', 'Panera Bread', PoiCategory.FOOD,
                                       GeoPoint(0, 0), website='https://www.panerabread.com'))
        show_poi_card(panel, poi)
        root.update()
        assert [b.cget('text') for b in panel._poi_action_buttons] == ['ORDER']
        button = panel._poi_action_buttons[0]
        assert button.winfo_ismapped()
        popup = panel._poi_card
        assert button.winfo_rootx() + button.winfo_width() <= popup.winfo_rootx() + popup.winfo_width()
        from ui.navigation.poi_models import PoiAppAvailability
        indicator = panel._poi_app_indicator
        indicator.set_availability(PoiAppAvailability.NOT_INSTALLED)
        indicator.invoke()
        requested, store = panel._execute_poi_action.call_args.args
        assert requested == poi
        assert store.kind is PoiActionKind.OPEN_ANDROID_APP
        assert store.provider_id == 'panera'
        panel._execute_poi_action.reset_mock()
        button.invoke()
        requested_poi, action = panel._execute_poi_action.call_args.args
        assert requested_poi.business_id == 'panera'
        assert action.kind is PoiActionKind.ORDER
    finally:
        root.destroy()


@pytest.mark.parametrize('mode', [ThemeMode.DARK, ThemeMode.LIGHT])
def test_borderless_business_card_has_icon_distinct_navigation_and_bottom_close(mode):
    controller = None
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f'X11 display unavailable: {error}')
    try:
        root.geometry('800x500')
        panel = tk.Frame(root)
        panel.pack(fill=tk.BOTH, expand=True)
        panel._poi_card = None
        panel._theme_bundle = theme_bundle(mode)
        panel.online_actions_allowed = True
        panel._waze_handler = Mock()
        panel._refresh_poi_action_buttons = Mock()
        panel._execute_poi_action = Mock()
        panel._navigate_to_poi = Mock()
        panel._navigate_to_poi_with_waze = Mock()
        panel._add_tooltip = Mock()
        poi = enrich_poi(PointOfInterest('store', "McDonald's", PoiCategory.FOOD, GeoPoint(0, 0)))
        search = Mock()
        search.poll_search_result.return_value = PoiSearchResult(PoiCategory.FOOD, 1, 0, 0, 0, 0, pois=(poi,))
        local = PoiAction(PoiActionKind.EXPLORE_3D, '3D Map', provider_id='local-3d')
        controller = NavigationPlacesController(search, Mock(), Mock(), local_3d_action=lambda value: local)
        poi = controller.poll_search_result().pois[0]
        show_poi_card(panel, poi)
        root.update()
        popup = panel._poi_card
        assert popup.overrideredirect()

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        widgets = tuple(descendants(popup))
        buttons = {w.cget('text'): w for w in widgets if isinstance(w, tk.Button)}
        icons = [w for w in widgets if getattr(w, '_poi_icon', None)]
        assert len(icons) == 1
        assert icons[0]._poi_icon.width() == 64
        gradient = icons[0].find_withtag('gradient')
        assert gradient
        assert icons[0].itemcget(gradient[0], 'fill') != icons[0].itemcget(gradient[-1], 'fill')
        assert buttons['Waze']._action_icon.width() > 0
        assert buttons['ORDER']._action_icon.width() > 0
        assert buttons['ORDER'].cget('fg') != buttons['ORDER'].cget('bg')
        for label in ('Earth', '3D Map'):
            assert buttons[label].winfo_ismapped()
            assert buttons[label].winfo_rootx() + buttons[label].winfo_width() <= popup.winfo_rootx() + popup.winfo_width()
        earth = next(a for a in poi.actions if a.provider_id == 'google-earth-explore')
        buttons['Earth'].invoke()
        panel._execute_poi_action.assert_any_call(poi, earth)
        buttons['3D Map'].invoke()
        panel._execute_poi_action.assert_any_call(poi, local)
        buttons['ORC Map'].invoke()
        panel._navigate_to_poi.assert_called_once_with(poi)
        buttons['Waze'].invoke()
        panel._navigate_to_poi_with_waze.assert_called_once_with(poi)
        assert buttons['CLOSE']._action_icon.width() > 0
        assert not any(icons[0].itemcget(item, 'text') == 'PLACE DETAILS' for item in icons[0].find_all() if icons[0].type(item) == 'text')
        assert icons[0].itemcget(icons[0].find_withtag('poi-title')[0], 'fill').lower() == poi.title_style.color.lower()
        assert buttons['CLOSE'].winfo_rooty() > buttons['ORDER'].winfo_rooty()
        assert buttons['CLOSE'].winfo_rooty() + buttons['CLOSE'].winfo_height() <= popup.winfo_rooty() + popup.winfo_height()
        indicator = panel._poi_app_indicator
        buttons['CLOSE'].invoke()
        assert indicator._icon is None
        assert not popup.winfo_exists()
        assert icons[0]._poi_icon is None
        assert buttons['ORDER']._action_icon is None
    finally:
        if controller is not None:
            controller.close()
        root.destroy()


def test_one_failed_poll_does_not_disable_future_poi_clicks():
    panel = Mock(_closed=False, _places_closed=False)
    panel.winfo_exists.return_value = True
    panel._poll_poi_events_once.side_effect = [RuntimeError('renderer restarting'), None]
    NavigationPlacesControls._poll_poi_events(panel)
    panel.after.assert_called_once_with(100, panel._poll_poi_events)
    NavigationPlacesControls._poll_poi_events(panel)
    assert panel.after.call_count == 2


def test_leaving_navigation_during_poll_does_not_rearm_old_view():
    panel = Mock(_closed=False, _places_closed=False)
    def close_during_poll():
        panel._places_closed = True
    panel._poll_poi_events_once.side_effect = close_during_poll
    NavigationPlacesControls._poll_poi_events(panel)
    panel.after.assert_not_called()


@pytest.mark.parametrize('availability', ['INSTALLED', 'NOT_INSTALLED', 'UNKNOWN', 'WEB_ONLY'])
def test_app_status_updates_only_the_current_live_card(availability):
    from ui.navigation.poi_models import PoiAppAvailability, PoiAppStatus
    from apps.orcUi.frontend.tk.navigation_poi_actions import poll_poi_app_status
    card, label, handler = Mock(), Mock(), Mock()
    panel = SimpleNamespace(_poi_card=card, _places_handler=handler,
        _theme_bundle=theme_bundle(ThemeMode.DARK),
        _poi_app_status_request=(7, 'store', card, label))
    handler.poll_app_status.return_value = PoiAppStatus(7, 'store', PoiAppAvailability[availability])
    poll_poi_app_status(panel)
    label.set_availability.assert_called_once_with(PoiAppAvailability[availability])
    label.reset_mock()
    panel._poi_app_status_request = (7, 'store', card, label)
    panel._poi_card = Mock()
    poll_poi_app_status(panel)
    label.set_availability.assert_not_called()


def test_app_indicator_only_opens_store_when_missing_enabled_and_explicitly_clicked():
    from apps.orcUi.frontend.tk.poi_app_indicator import PoiAppIndicator
    from ui.navigation.poi_models import PoiAppAvailability
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f'X11 display unavailable: {error}')
    try:
        store = Mock()
        indicator = PoiAppIndicator(root, icon=None, theme=theme_bundle(ThemeMode.DARK).ui, open_store=store)
        for availability in PoiAppAvailability:
            indicator.set_availability(availability)
            store.assert_not_called()
        for availability in (PoiAppAvailability.INSTALLED, PoiAppAvailability.UNKNOWN, PoiAppAvailability.WEB_ONLY):
            indicator.set_availability(availability)
            indicator.invoke()
        store.assert_not_called()
        indicator.set_availability(PoiAppAvailability.NOT_INSTALLED)
        indicator.set_enabled(False)
        indicator.invoke()
        store.assert_not_called()
        indicator.set_enabled(True)
        indicator.invoke()
        store.assert_called_once_with()
    finally:
        root.destroy()
