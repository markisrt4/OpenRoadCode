# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Present asynchronous place handoffs through navigation request contracts."""

from ui.navigation.poi_models import PoiActionKind, PoiAppStatus, PoiAppAvailability


def request_poi_app_status(panel, poi, label):
    """Scope a background availability observation to this exact popup."""
    panel._poi_app_status_request = None
    handler = panel.__dict__.get('_places_handler')
    request_id = handler.request_app_status(poi) if handler is not None else None
    if type(request_id) is not int:
        label.set_availability(PoiAppAvailability.UNKNOWN)
        return
    panel._poi_app_status_request = (request_id, poi.poi_id, panel._poi_card, label)


def poll_poi_app_status(panel):
    """Apply only results for the current live card, never a retired one."""
    pending = panel.__dict__.get('_poi_app_status_request')
    if pending is None:
        return
    result = panel._places_handler.poll_app_status()
    if not isinstance(result, PoiAppStatus) or (result.request_id, result.poi_id) != pending[:2]:
        return
    panel._poi_app_status_request = None
    card, label = pending[2:]
    if card is not panel._poi_card or not card.winfo_exists() or not label.winfo_exists():
        return
    label.set_availability(result.availability)


def execute_poi_action(panel, poi, action) -> None:
    """Request a handoff. @param panel View. @param poi Place. @param action Action."""
    if action.kind is not PoiActionKind.EXPLORE_3D and not panel.online_actions_allowed:
        panel._shortcut_status.set('Offline mode: go online to order or open websites')
        return
    if panel._poi_launching:
        return
    request_id = panel._places_handler.request_action(poi, action)
    if request_id is None:
        return
    panel._poi_action_request = (request_id, panel._poi_card)
    panel._poi_launching = True
    panel._refresh_poi_action_buttons()
    panel._shortcut_status.set(f'Opening {action.label.casefold()}…')


def poll_poi_launch_results(panel) -> None:
    """Apply current completion. @param panel Mounted navigation view."""
    result = panel._places_handler.poll_action_result()
    if result is None:
        return
    pending = panel._poi_action_request
    if pending is None or pending[0] != result.request_id:
        return
    panel._poi_action_request = None
    panel._poi_launching = False
    panel._refresh_poi_action_buttons()
    panel._shortcut_status.set(result.status)
    card = pending[1]
    if result.success and card is panel._poi_card and card is not None and card.winfo_exists():
        card.destroy()
