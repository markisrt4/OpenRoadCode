# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Keep POI app/web handoffs off the Tk thread and apply results in the UI poll."""
from __future__ import annotations

from queue import Empty
from threading import Thread
from typing import TYPE_CHECKING

from apps.launchers.android_app_launcher import AndroidAppLauncherError
from apps.launchers.android_intent_launcher import AndroidIntentLauncherError
from controllers.poi import PoiAction, PointOfInterest

if TYPE_CHECKING:
    from .navigation_panel import NavigationPanel


def execute_poi_action(panel: NavigationPanel, poi: PointOfInterest, action: PoiAction) -> None:
    """Start one handoff, guarding mode and duplicate clicks before the worker."""
    if not panel.online_actions_allowed:
        panel._shortcut_status.set("Offline mode: go online to order or open websites")
        return
    if panel._poi_launching:
        return
    panel._poi_launching = True
    card = panel._poi_card
    panel._refresh_poi_action_buttons()
    panel._shortcut_status.set(f"Opening {action.label.casefold()}…")

    def launch() -> None:
        try:
            if not panel.online_actions_allowed:
                raise ValueError("Offline mode: go online to open this destination")
            status = panel._poi_action_executor.execute(poi, action)
        except (AndroidAppLauncherError, AndroidIntentLauncherError, ValueError) as exc:
            panel._poi_launch_results.put((card, f"Launch failed: {exc}", False))
        else:
            panel._poi_launch_results.put((card, status, True))

    panel._poi_launch_worker = Thread(target=launch, name="orc-poi-launch", daemon=True)
    panel._poi_launch_worker.start()


def poll_poi_launch_results(panel: NavigationPanel) -> None:
    """Apply completed handoffs on the Tk thread and retain failures for retry."""
    try:
        card, status, success = panel._poi_launch_results.get_nowait()
    except Empty:
        return
    panel._poi_launching = False
    panel._refresh_poi_action_buttons()
    panel._shortcut_status.set(status)
    # Leave failures open for retry, and do not close a different/new POI card.
    if success and card is panel._poi_card and card is not None and card.winfo_exists():
        card.destroy()
