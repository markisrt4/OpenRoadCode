# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""HOME-screen assembly for the integrated orcUi Tk frontend."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from apps.orcUi.navigation_presenter import (
    AttitudePresentationState,
    PositionPresentationState,
)
from apps.orcUi.trip_presenter import TripPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from ui.navigation import MapRequestHandlerIf
from ui.theme import ThemeBundle

from .context_rail import ContextRail
from .home_map_panel import HomeMapPanel
from .shell_content import add_summary, panel


def build_home_screen(
    parent: tk.Frame,
    *,
    map_request_handler: MapRequestHandlerIf,
    theme: ThemeBundle,
    vehicle_state: VehiclePresentationState,
    trip_state: TripPresentationState,
    position_state: PositionPresentationState,
    attitude_state: AttitudePresentationState,
    on_expand_context: Callable[[str], None],
    radio_factory: Callable[[tk.Misc], tk.Widget] | None,
    media_factory: Callable[[tk.Misc], tk.Widget] | None,
) -> tuple[HomeMapPanel, ContextRail]:
    """Build HOME content and return the stateful child widgets."""
    ui = theme.ui
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_columnconfigure(1, weight=0, minsize=ContextRail.WIDTH)
    parent.grid_rowconfigure(0, weight=3)
    parent.grid_rowconfigure(1, weight=2)

    map_panel = HomeMapPanel(
        parent,
        map_request_handler=map_request_handler,
        theme=theme,
    )
    map_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))

    context = ContextRail(parent, on_expand=on_expand_context, theme=theme)
    context.update_vehicle_state(vehicle_state)
    context.update_trip_state(trip_state)
    context.update_position_state(position_state)
    context.update_attitude_state(attitude_state)
    context.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))

    lower = tk.Frame(parent, bg=ui.background)
    lower.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(5, 0))
    lower.grid_columnconfigure(0, weight=4)
    lower.grid_columnconfigure(1, weight=1)
    lower.grid_rowconfigure(0, weight=1)

    radio = panel(lower, "RADIO", ui.accent_warning, theme=theme)
    radio.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    if radio_factory is None:
        add_summary(
            radio,
            "No radio active",
            "Choose RF or streaming",
            theme=theme,
        )
    else:
        radio_factory(radio).pack(fill=tk.BOTH, expand=True)

    media = panel(lower, "MEDIA", ui.accent_primary, theme=theme)
    media.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    if media_factory is None:
        add_summary(media, "No media", "Playback service", theme=theme)
    else:
        media_factory(media).pack(fill=tk.BOTH, expand=True)

    return map_panel, context
