# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import Mock

from apps.orcUi.frontend.tk.navigation_places_controls import NavigationPlacesControls


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
