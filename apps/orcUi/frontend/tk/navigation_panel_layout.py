# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk widget construction helpers for the ORC navigation panel."""

import logging
import tkinter as tk

from common.logging.structured import event
from ui.navigation.map_layer_controls import MapLayerAction, MapLayerControls

from .navigation_poi_card_layout import build_poi_card


def build_navigation_panel(panel) -> None:
    """Build the navigation panel widget hierarchy."""
    ui = panel._theme_bundle.ui
    panel.grid_rowconfigure(1, weight=1)
    panel.grid_rowconfigure(2, weight=0)
    panel.grid_columnconfigure(0, weight=1)
    bar = tk.Frame(panel, bg=ui.surface_alt, height=48, highlightthickness=0)
    bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
    bar.grid_propagate(False)
    # Drawer widgets are built after the native host so they occupy a separate
    # grid column, never covering an X11 child window.
    panel._navigation_toolbar = bar

    guidance = tk.Frame(panel, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
    guidance.grid(row=2, column=0, sticky="ew", pady=(4, 0))
    tk.Label(
        guidance, text="ROUTE", bg=ui.surface, fg=ui.text_muted, font=("Sans", 8, "bold")
    ).pack(side=tk.LEFT, padx=6)
    tk.Label(
        guidance,
        textvariable=panel._guidance_instruction,
        bg=ui.surface,
        fg=ui.text,
        font=("Sans", 10, "bold"),
        anchor="w",
    ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 6), pady=4)
    panel._simulate_button = tk.Button(
        guidance,
        text="Simulate",
        command=panel._toggle_route_simulation,
        bg=ui.control_background,
        fg=ui.accent_warning,
        activebackground=ui.control_active,
        activeforeground="#ffffff",
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=ui.border,
        font=("Sans", 8, "bold"),
        state=tk.DISABLED,
    )
    panel._simulate_button.pack(side=tk.RIGHT, padx=(4, 8), pady=3)
    panel._cancel_route_button = tk.Button(
        guidance,
        text="End route",
        command=panel._cancel_route,
        bg=ui.control_background,
        fg=ui.accent_danger,
        activebackground=ui.control_active,
        activeforeground="#ffffff",
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=ui.border,
        font=("Sans", 8, "bold"),
        state=tk.DISABLED,
    )
    panel._cancel_route_button.pack(side=tk.RIGHT, padx=(4, 2), pady=3)
    tk.Label(
        guidance,
        textvariable=panel._guidance_detail,
        bg=ui.surface,
        fg=ui.text_muted,
        font=("Sans", 8),
        anchor="e",
    ).pack(side=tk.RIGHT, padx=(6, 4), pady=4)

    body = tk.Frame(panel, bg=ui.background)
    body.grid(row=1, column=0, sticky="nsew")
    body.grid_rowconfigure(0, weight=1)
    body.grid_columnconfigure(0, weight=1)
    panel._map_host = tk.Frame(
        body, bg=ui.background, highlightthickness=1, highlightbackground=ui.border
    )
    panel._map_host.grid(row=0, column=0, sticky="nsew")
    panel._loading_cover = tk.Label(body, text="Loading Terrain…", bg=ui.background, fg=ui.text)
    panel._loading_cover.grid(row=0, column=0, sticky="nsew")
    panel._loading_cover.grid_remove()
    panel._map_retry_button = tk.Button(
        body,
        text="RETRY MAP",
        command=panel._map_platform.request_retry if panel._map_platform is not None else None,
        bg=ui.control_background,
        fg=ui.control_text,
        activebackground=ui.control_active,
        relief=tk.FLAT,
        bd=0,
        font=("Sans", 11, "bold"),
        padx=16,
        pady=10,
    )
    panel._map_host.bind("<Configure>", panel._log_map_allocation, add="+")
    if panel._experience_handler is not None:
        from frontends.tk.navigation_experience_controls import NavigationExperienceControls

        panel._experience_controls = NavigationExperienceControls(
            bar,
            drawer_parent=body,
            drawer_row=0,
            drawer_column=1,
            handler=panel._experience_handler,
            theme=panel._theme_bundle,
            on_open=lambda: panel.set_navigation_drawer_visible(True),
            on_close=lambda: panel.set_navigation_drawer_visible(False),
        )
        panel._experience_controls.pack(fill=tk.X, expand=True)
        panel._build_radar_controls(panel._experience_controls.overlay_frame)
    else:
        panel._build_radar_controls(bar)

    panel._map_controls_handle = tk.Button(
        body,
        text="CONTROLS ›",
        command=panel._toggle_map_controls_drawer,
        bg=ui.control_background,
        fg=ui.accent_primary,
        activebackground=ui.control_active,
        activeforeground="#ffffff",
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        font=("Sans", 9, "bold"),
        cursor="hand2",
    )
    controls = tk.Frame(
        body,
        bg=ui.surface_alt,
        width=224,
        highlightbackground=ui.control_background,
        highlightthickness=1,
    )
    controls.pack_propagate(False)
    controls.grid_propagate(False)
    panel._map_controls = controls
    panel._native_camera_controls = controls
    panel._map_controls_toggle = panel._control(
        controls, "Map controls   ⌃", panel._toggle_map_controls_drawer, ui.text
    )
    panel._map_controls_toggle.configure(anchor="w", font=("Sans", 10, "bold"), pady=7)
    panel._map_controls_toggle.pack(fill=tk.X, padx=4, pady=4)
    rail = tk.Frame(controls, bg=ui.surface_alt)
    panel._map_controls_rail = rail
    rail.grid_rowconfigure(0, weight=1)
    rail.grid_columnconfigure(0, weight=1)
    pages = {name: tk.Frame(rail, bg=ui.surface_alt) for name in ("camera", "layers", "terrain")}
    panel._map_control_pages = pages
    panel._map_controls_page = "camera"
    content = pages["camera"]
    content.grid_columnconfigure(0, weight=1)
    for row, weight in ((0, 2), (1, 3), (2, 1), (3, 1), (4, 1)):
        content.grid_rowconfigure(row, weight=weight)
    drawer_buttons = []
    drawer_groups = []

    def button(parent, text, command, row, column, accent=ui.control_text):
        widget = panel._control(parent, text, command, accent)
        widget.configure(
            font=("Sans", 9, "bold"),
            pady=6,
            highlightthickness=1,
            highlightbackground=ui.control_background,
        )
        widget.grid(row=row, column=column, sticky="nsew", padx=2, pady=2)
        drawer_buttons.append(widget)
        return widget

    orientation = tk.Frame(content, bg=ui.surface_alt)
    orientation.grid(row=0, column=0, sticky="nsew")
    drawer_groups.append(orientation)
    for row in range(2):
        orientation.grid_rowconfigure(row, weight=1)
    for column in range(2):
        orientation.grid_columnconfigure(column, weight=1, uniform="orientation")
    panel._follow_button = button(
        orientation, "◉ Follow", panel._toggle_follow, 0, 0, ui.accent_success
    )
    panel._add_tooltip(panel._follow_button, "Toggle following the vehicle")
    recenter = button(orientation, "⌖ Recenter", panel._recenter, 0, 1)
    panel._add_tooltip(recenter, "Center on the vehicle and enable following")
    north = button(orientation, "↑ North up", panel._north_up, 1, 0)
    panel._add_tooltip(north, "Rotate north to the top (turns follow off)")
    dimension = button(orientation, "2D / 3D", panel._toggle_map_dimension, 1, 1)
    panel._add_tooltip(dimension, "Switch between overhead 2D and tilted 3D view")
    panel.set_follow_enabled(panel._follow_enabled)

    movement = tk.Frame(content, bg=ui.surface_alt)
    movement.grid(row=1, column=0, sticky="nsew")
    drawer_groups.append(movement)
    movement.grid_rowconfigure(0, weight=1)
    movement.grid_columnconfigure(0, weight=3)
    movement.grid_columnconfigure(1, weight=1)
    pan = tk.Frame(movement, bg=ui.surface_alt)
    pan.grid(row=0, column=0, sticky="nsew")
    for column in range(3):
        pan.grid_columnconfigure(column, weight=1, uniform="pan")
        pan.grid_rowconfigure(column, weight=1, uniform="pan")
    for row, column, label, up, right in (
        (0, 1, "↑", 1, 0),
        (1, 0, "←", 0, -1),
        (1, 2, "→", 0, 1),
        (2, 1, "↓", -1, 0),
    ):
        widget = button(pan, label, lambda u=up, r=right: panel._pan(u, r), row, column)
        direction = {(1, 0): "up", (-1, 0): "down", (0, -1): "left", (0, 1): "right"}[(up, right)]
        panel._add_tooltip(widget, f"Pan the map {direction} on screen (turns follow off)")
    center = button(pan, "⌖", panel._recenter, 1, 1, ui.accent_primary)
    panel._add_tooltip(center, "Recenter on the vehicle")
    zoom = tk.Frame(movement, bg=ui.surface_alt)
    zoom.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    zoom.grid_columnconfigure(0, weight=1)
    zoom.grid_rowconfigure(0, weight=1)
    zoom.grid_rowconfigure(1, weight=1)
    for row, text, delta in ((0, "＋", 1), (1, "−", -1)):
        widget = button(
            zoom, text, lambda d=delta: panel._change_zoom(d), row, 0, ui.accent_primary
        )
        widget.configure(font=("Sans", 15, "bold"))
        panel._add_tooltip(widget, "Zoom in" if delta > 0 else "Zoom out")
    readout = tk.Label(
        zoom, textvariable=panel._zoom_text, bg=ui.surface_alt, fg=ui.text_muted, font=("Sans", 8)
    )
    readout.grid(row=2, column=0)
    panel._add_tooltip(readout, "Current map zoom level")
    tilt = tk.Frame(content, bg=ui.surface_alt)
    tilt.grid(row=2, column=0, sticky="nsew")
    drawer_groups.append(tilt)
    tilt.grid_rowconfigure(0, weight=1)
    for column in range(2):
        tilt.grid_columnconfigure(column, weight=1, uniform="tilt")
    for column, text, delta in ((0, "↘ Less tilt", -5), (1, "↗ More tilt", 5)):
        widget = button(tilt, text, lambda d=delta: panel._change_pitch(d), 0, column)
        panel._add_tooltip(
            widget, ("Increase" if delta > 0 else "Decrease") + " map tilt (turns follow off)"
        )

    panel._layer_buttons = {}
    navigation = tk.Frame(content, bg=ui.surface_alt)
    navigation.grid(row=3, column=0, sticky="nsew")
    navigation.grid_rowconfigure(0, weight=1)
    drawer_groups.append(navigation)
    for column in range(2):
        navigation.grid_columnconfigure(column, weight=1, uniform="pages")
    button(navigation, "Layers ›", lambda: panel._show_map_controls_page("layers"), 0, 0)
    button(navigation, "Terrain ›", lambda: panel._show_map_controls_page("terrain"), 0, 1)

    def section(name, title, actions):
        page = pages[name]
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)
        button(page, "‹ Back to controls", lambda: panel._show_map_controls_page("camera"), 0, 0)
        tk.Label(page, text=title, bg=ui.surface_alt, fg=ui.text, font=("Sans", 10, "bold")).grid(
            row=1, column=0, pady=2
        )
        items = tk.Frame(page, bg=ui.surface_alt)
        items.grid(row=2, column=0, sticky="nsew")
        drawer_groups.append(items)
        for row in range(2):
            items.grid_rowconfigure(row, weight=1)
        for column in range(2):
            items.grid_columnconfigure(column, weight=1, uniform="layers")
        for index, (action, label) in enumerate(actions):
            widget = button(
                items,
                label,
                lambda selected=action: panel._request_layer(selected),
                index // 2,
                index % 2,
            )
            widget.configure(state=tk.DISABLED)
            panel._add_tooltip(widget, "Requires an installed layer in Terrain mode")
            panel._layer_buttons[action] = widget

    section(
        "layers",
        "Layers",
        (
            (MapLayerAction.IMAGERY, "Imagery"),
            (MapLayerAction.BUILDINGS, "Buildings"),
            (MapLayerAction.ROADS, "Roads"),
            (MapLayerAction.PLACES, "Places"),
        ),
    )
    section(
        "terrain",
        "Terrain options",
        (
            (MapLayerAction.RELIEF, "Relief"),
            (MapLayerAction.HEIGHT, "Height 1×"),
            (MapLayerAction.CUES, "Terrain cues"),
            (MapLayerAction.GRID, "Grid"),
        ),
    )
    reset = button(content, "⟳ Reset view", panel._reset_map_view, 4, 0)
    panel._add_tooltip(reset, "Reset Terrain view; in Map mode recenter on the vehicle")

    last_compact = None

    def fit_controls(_event):
        nonlocal last_compact
        # Base this on the fixed outer drawer, not the body whose height changes
        # when the header shrinks, to avoid a compact/regular geometry loop.
        compact = controls.winfo_height() < 320
        if compact == last_compact:
            return
        last_compact = compact
        for widget in drawer_buttons:
            widget.configure(font=("Sans", 8 if compact else 9, "bold"), pady=0 if compact else 6)
            widget.grid_configure(pady=0 if compact else 2, padx=1 if compact else 2)
        panel._map_controls_toggle.configure(
            font=("Sans", 8 if compact else 10, "bold"), pady=0 if compact else 7
        )
        # Prevent hidden pages' requested sizes from setting the viewport size.
        for page in pages.values():
            page.grid_propagate(False)
        for group in drawer_groups:
            group.grid_propagate(False)

    rail.bind("<Configure>", fit_controls)
    panel._show_map_controls_page("camera")
    panel._apply_layer_controls(MapLayerControls(), False)

    panel.set_map_controls_drawer_state(panel._drawer_state)


def show_poi_card(panel, poi) -> None:
    build_poi_card(panel, poi, tk)


def log_map_allocation(panel, _event=None) -> None:
    """Trace settled Tk geometry separately from the native viewport."""
    logger = logging.getLogger("navigation.map.layout")
    if not logger.isEnabledFor(logging.DEBUG):
        return
    host = panel._map_host
    body = host.master
    event(
        logger,
        logging.DEBUG,
        "map.host_allocation",
        f"expanded={panel._drawer_state.expanded} "
        f"body={body.winfo_width()}x{body.winfo_height()} "
        f"host={host.winfo_width()}x{host.winfo_height()} "
        f"host_id={host.winfo_id()} "
        f"controls_manager={panel._map_controls.winfo_manager() or 'hidden'}",
    )
