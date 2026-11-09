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
from ui.navigation.poi_models import PoiActionKind, PoiCategory, PointOfInterest


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
        poi = enrich_poi(PointOfInterest('store', 'Panera Bread', PoiCategory.FOOD,
                                       GeoPoint(0, 0), website='https://www.panerabread.com'))
        show_poi_card(panel, poi)
        root.update()
        assert [b.cget('text') for b in panel._poi_action_buttons] == ['ORDER']
        button = panel._poi_action_buttons[0]
        assert button.winfo_ismapped()
        popup = panel._poi_card
        assert button.winfo_rootx() + button.winfo_width() <= popup.winfo_rootx() + popup.winfo_width()
        button.invoke()
        requested_poi, action = panel._execute_poi_action.call_args.args
        assert requested_poi.business_id == 'panera'
        assert action.kind is PoiActionKind.ORDER
    finally:
        root.destroy()


def test_borderless_business_card_has_icon_distinct_navigation_and_bottom_close():
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
        panel._waze_handler = Mock()
        panel._refresh_poi_action_buttons = Mock()
        panel._execute_poi_action = Mock()
        panel._navigate_to_poi = Mock()
        panel._navigate_to_poi_with_waze = Mock()
        poi = enrich_poi(PointOfInterest('store', "McDonald's", PoiCategory.FOOD, GeoPoint(0, 0)))
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
        icons = [w for w in widgets if isinstance(w, tk.Label) and getattr(w, '_poi_icon', None)]
        assert len(icons) == 1
        assert icons[0]._poi_icon.width() == 64
        buttons['ORC Map'].invoke()
        panel._navigate_to_poi.assert_called_once_with(poi)
        buttons['Waze'].invoke()
        panel._navigate_to_poi_with_waze.assert_called_once_with(poi)
        assert buttons['CLOSE'].winfo_rooty() > buttons['ORDER'].winfo_rooty()
        assert buttons['CLOSE'].winfo_rooty() + buttons['CLOSE'].winfo_height() <= popup.winfo_rooty() + popup.winfo_height()
        buttons['CLOSE'].invoke()
        assert not popup.winfo_exists()
        assert icons[0]._poi_icon is None
    finally:
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
