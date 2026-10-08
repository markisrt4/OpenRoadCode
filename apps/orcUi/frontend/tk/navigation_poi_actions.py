# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Present asynchronous place handoffs through navigation request contracts."""


def execute_poi_action(panel, poi, action) -> None:
    """Request a handoff. @param panel View. @param poi Place. @param action Action."""
    if not panel.online_actions_allowed:
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
