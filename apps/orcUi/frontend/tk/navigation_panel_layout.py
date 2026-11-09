# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk widget construction helpers for the ORC navigation panel."""

import tkinter as tk

from .navigation_earth_control import build_earth_control, build_poi_icon_button, load_poi_action_icon
from .poi_card_header import PoiCardHeader

from ui.navigation.poi_models import PoiActionKind


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

    guidance = tk.Frame(
        panel, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border
    )
    guidance.grid(row=2, column=0, sticky="ew", pady=(4, 0))
    tk.Label(guidance, text="ROUTE", bg=ui.surface, fg=ui.text_muted,
             font=("Sans", 8, "bold")).pack(side=tk.LEFT, padx=6)
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
    panel._loading_cover = tk.Label(body, text='Loading Terrain…',
                                    bg=ui.background, fg=ui.text)
    panel._loading_cover.grid(row=0, column=0, sticky='nsew')
    panel._loading_cover.grid_remove()
    panel._map_retry_button = tk.Button(body, text='RETRY MAP',
        command=panel._map_platform.request_retry if panel._map_platform is not None else None,
        bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active,
        relief=tk.FLAT, bd=0, font=('Sans', 11, 'bold'), padx=16, pady=10)
    panel._map_host.bind("<Configure>", panel._log_map_allocation, add="+")
    if panel._experience_handler is not None:
        from frontends.tk.navigation_experience_controls import NavigationExperienceControls
        panel._experience_controls = NavigationExperienceControls(
            bar, drawer_parent=body, drawer_row=0, drawer_column=1,
            handler=panel._experience_handler, theme=panel._theme_bundle,
            on_open=lambda: panel.set_navigation_drawer_visible(True),
            on_close=lambda: panel.set_navigation_drawer_visible(False))
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
    controls = tk.Frame(body, bg=ui.surface_alt, width=54, highlightthickness=0)
    controls.pack_propagate(False)
    panel._map_controls = controls
    panel._map_controls_toggle = tk.Button(
        controls,
        text="Hide controls  ›",
        command=panel._toggle_map_controls_drawer,
        bg=ui.control_background,
        fg=ui.accent_primary,
        activebackground=ui.control_active,
        activeforeground="#ffffff",
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        font=("Sans", 10, "bold"),
        padx=5,
        pady=10,
    )
    panel._map_controls_toggle.pack(fill=tk.X)
    panel._native_camera_controls = controls
    rail = tk.Frame(controls, bg=ui.surface_alt)
    panel._map_controls_rail = rail
    rail.grid_columnconfigure(0, weight=1)
    for row, weight in ((0, 3), (1, 3), (2, 1), (3, 1), (4, 1)):
        rail.grid_rowconfigure(row, weight=weight, uniform="camera")
    orientation = tk.Frame(rail, bg=ui.surface_alt)
    orientation.grid(row=0, column=0, sticky="nsew", padx=3, pady=2)
    orientation.grid_propagate(False)
    orientation.grid_columnconfigure(0, weight=1)
    for row in range(3):
        orientation.grid_rowconfigure(row, weight=1, uniform="orientation")
    panel._follow_button = panel._control(
        orientation, "◉  Follow", panel._toggle_follow, ui.accent_success
    )
    panel._follow_button.grid(row=0, column=0, sticky="nsew", pady=1)
    panel._add_tooltip(panel._follow_button, "Toggle following the vehicle")
    for row, label, command, accent, description in (
        (1, "↑  North up", panel._north_up, ui.text, "Rotate north to the top (turns follow off)"),
        (2, "⌖  Recenter", panel._recenter, ui.accent_success, "Center on the vehicle and enable following"),
    ):
        button = panel._control(orientation, label, command, accent)
        button.grid(row=row, column=0, sticky="nsew", pady=1)
        panel._add_tooltip(button, description)
    panel.set_follow_enabled(panel._follow_enabled)
    pan = tk.Frame(rail, bg=ui.surface_alt)
    pan.grid(row=1, column=0, sticky="nsew", padx=3, pady=2)
    pan.grid_propagate(False)
    for index in range(3):
        pan.grid_rowconfigure(index, weight=1, uniform="pan")
        pan.grid_columnconfigure(index, weight=1, uniform="pan")
    for row, column, label, up, right in (
        (0, 1, "▲", 1, 0),
        (1, 0, "◀", 0, -1),
        (1, 2, "▶", 0, 1),
        (2, 1, "▼", -1, 0),
    ):
        button = tk.Button(
            pan,
            text=label,
            command=lambda u=up, r=right: panel._pan(u, r),
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=0,
            font=("Sans", 11, "bold"),
            borderwidth=0,
            width=1,
            height=1,
            padx=4,
            pady=4,
        )
        button.grid(row=row, column=column, sticky="nsew", padx=1, pady=1)
        direction = {(1, 0): "up", (0, -1): "left", (0, 1): "right", (-1, 0): "down"}[(up, right)]
        panel._add_tooltip(button, f"Pan the map {direction} on screen (turns follow off)")
    zoom = tk.Frame(rail, bg=ui.surface_alt)
    zoom.grid(row=2, column=0, sticky="nsew", padx=3, pady=2)
    zoom.grid_propagate(False)
    zoom.grid_rowconfigure(0, weight=1)
    for column in range(2):
        zoom.grid_columnconfigure(column, weight=1, uniform="zoom")
    zoom_in = panel._control(zoom, "+", lambda: panel._change_zoom(1), ui.accent_primary)
    zoom_in.configure(font=("Sans", 19, "bold"), pady=8)
    panel._add_tooltip(zoom_in, "Zoom in")
    zoom_in.grid(row=0, column=0, sticky="nsew", padx=1)
    zoom_out = panel._control(zoom, "−", lambda: panel._change_zoom(-1), ui.accent_primary)
    zoom_out.configure(font=("Sans", 19, "bold"), pady=8)
    panel._add_tooltip(zoom_out, "Zoom out")
    zoom_out.grid(row=0, column=1, sticky="nsew", padx=1)
    zoom_label = tk.Label(
        zoom,
        textvariable=panel._zoom_text,
        bg=ui.control_background,
        fg=ui.text,
        font=("Sans", 8, "bold"),
    )
    zoom_label.place(relx=0.5, y=2, anchor="n")
    zoom_label.lift()
    panel._add_tooltip(zoom_label, "Current map zoom level")
    dimension = tk.Frame(rail, bg=ui.surface_alt)
    dimension.grid(row=3, column=0, sticky="nsew", padx=4, pady=2)
    dimension.grid_propagate(False)
    dimension.grid_rowconfigure(0, weight=1)
    dimension.grid_columnconfigure(0, weight=1)
    dimension_button = panel._control(dimension, "", panel._toggle_map_dimension, ui.accent_primary)
    dimension_button.configure(textvariable=panel._dimension_text)
    dimension_button.grid(row=0, column=0, sticky="nsew")
    panel._add_tooltip(dimension_button, "Switch between overhead 2D and tilted 3D view")
    tilt = tk.Frame(rail, bg=ui.surface_alt)
    tilt.grid(row=4, column=0, sticky="nsew", padx=3, pady=2)
    tilt.grid_propagate(False)
    tilt.grid_rowconfigure(0, weight=1)
    for column in range(2):
        tilt.grid_columnconfigure(column, weight=1, uniform="tilt")
    for column, (label, command, accent, description) in enumerate((
        ("↗", lambda: panel._change_pitch(5), ui.accent_warning, "Increase map tilt (turns follow off)"),
        ("↘", lambda: panel._change_pitch(-5), ui.accent_warning, "Decrease map tilt (turns follow off)"),
    )):
        button = panel._control(tilt, label, command, accent)
        panel._add_tooltip(button, description)
        button.grid(row=0, column=column, sticky="nsew", padx=1)

    panel.set_map_controls_drawer_state(panel._drawer_state)


def show_poi_card(panel, poi) -> None:
    """Show selected business information above the native map window."""
    ui = panel._theme_bundle.ui
    if panel._poi_card is not None and panel._poi_card.winfo_exists():
        panel._poi_card.destroy()

    popup = tk.Toplevel(panel)
    popup.title(poi.name)
    popup.overrideredirect(True)
    popup.configure(bg=ui.surface_alt)
    popup.transient(panel.winfo_toplevel())
    popup.resizable(False, False)
    popup.attributes("-topmost", True)
    panel._poi_card = popup

    width = min(480, panel.winfo_screenwidth() - 16)
    other_actions = tuple(action for action in poi.actions
                          if action.kind in {PoiActionKind.ORDER, PoiActionKind.OPEN_WEBSITE, PoiActionKind.OPEN_ANDROID_APP}
                          and action.provider_id != "google-earth-explore")
    height = 330 if other_actions else 280
    has_waze = panel.__dict__.get('_waze_handler') is not None
    panel.update_idletasks()
    x = panel.winfo_rootx() + max(0, (panel.winfo_width() - width) // 2)
    y = panel.winfo_rooty() + max(0, (panel.winfo_height() - height) // 2)
    x = max(8, min(x, panel.winfo_screenwidth() - width - 8))
    y = max(8, min(y, panel.winfo_screenheight() - height - 8))
    popup.geometry(f"{width}x{height}+{x}+{y}")

    shell = tk.Frame(
        popup,
        bg=ui.surface_alt,
        highlightthickness=1, highlightbackground=ui.accent_primary,
    )
    shell.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

    panel._earth_button = None
    earth_action = next((action for action in poi.actions
                         if action.provider_id == "google-earth-explore"), None)

    details: list[str] = []
    if poi.brand and poi.brand.casefold() != poi.name.casefold():
        details.append(poi.brand)
    if poi.address:
        details.append(poi.address)
    elif poi.source_class == "saved-destination":
        details.append("Saved destination")
    else:
        details.append(poi.category.name.replace("_", " ").title())

    header = PoiCardHeader(shell, title=poi.name, details='  •  '.join(details), icon=poi.icon, theme=ui)
    header.pack(fill=tk.X)
    tk.Frame(shell, height=1, bg=ui.border).pack(fill=tk.X)
    frame = tk.Frame(shell, bg=ui.surface_alt, padx=12, pady=8)
    frame.pack(fill=tk.BOTH, expand=True)

    close = tk.Button(frame, text='CLOSE', command=popup.destroy,
        bg=ui.control_background, fg=ui.text_muted, activebackground=ui.control_active,
        activeforeground=ui.text, relief=tk.FLAT, borderwidth=0,
        highlightthickness=1, highlightbackground=ui.border, highlightcolor=ui.accent_primary,
        font=('Sans', 10, 'bold'), pady=6)
    close.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    popup.bind('<Escape>', lambda _event: popup.destroy())

    buttons = tk.Frame(frame, bg=ui.surface_alt)
    buttons.pack()

    navigate = tk.Frame(buttons, bg=ui.surface_alt)
    navigate.pack(side=tk.LEFT, padx=(0, 8))
    tk.Label(navigate, text='NAVIGATE WITH', bg=ui.surface_alt, fg=ui.text_muted,
             font=('Sans', 8, 'bold')).pack()
    nav_buttons = tk.Frame(navigate, bg=ui.surface_alt)
    nav_buttons.pack()
    build_poi_icon_button(panel, nav_buttons, "navigate.png", "ORC Map",
                          lambda: panel._navigate_to_poi(poi), tk)
    panel._poi_action_buttons = []
    if has_waze:
        waze_button = build_poi_icon_button(panel, nav_buttons, 'waze.png', 'Waze',
                                           lambda: panel._navigate_to_poi_with_waze(poi), tk)
        panel._poi_action_buttons.append(waze_button)
    explore = tk.Frame(buttons, bg=ui.surface_alt)
    explore.pack(side=tk.LEFT)
    local_action = next((a for a in poi.actions if a.kind is PoiActionKind.EXPLORE_3D), None)
    if earth_action is not None or local_action is not None:
        tk.Label(explore, text='EXPLORE', bg=ui.surface_alt, fg=ui.text_muted,
                 font=('Sans', 8, 'bold')).pack()
    explore_buttons = tk.Frame(explore, bg=ui.surface_alt)
    explore_buttons.pack()
    if earth_action is not None:
        build_earth_control(panel, explore_buttons, poi, earth_action, tk)

    panel._local_3d_button = None
    if local_action is not None:
        panel._local_3d_button = build_poi_icon_button(
            panel, explore_buttons, "map_3d.png", "3D Map",
            lambda: panel._execute_poi_action(poi, local_action), tk)
        panel._add_tooltip(panel._local_3d_button, "Offline 3D exploration; coverage depends on installed map packs")

    extra_buttons = tk.Frame(frame, bg=ui.surface_alt)
    if other_actions:
        extra_buttons.pack(pady=(6, 0))
    for action in other_actions:
        if (action.kind in {PoiActionKind.ORDER, PoiActionKind.OPEN_WEBSITE, PoiActionKind.OPEN_ANDROID_APP}
                and action.provider_id != "google-earth-explore"):
            ordering = action.kind is PoiActionKind.ORDER
            icon = load_poi_action_icon(extra_buttons, 'order.png', tk) if ordering else None
            size = {'width': 180, 'height': 42, 'padx': 12} if ordering else {
                'width': max(12, min(28, len(action.label) + 2)), 'height': 2}
            button = tk.Button(
                extra_buttons,
                text=action.label,
                image=icon if icon is not None else '', compound=tk.LEFT,
                state=tk.NORMAL if panel.online_actions_allowed else tk.DISABLED,
                disabledforeground=ui.text_muted,
                command=lambda selected=action: panel._execute_poi_action(poi, selected),
                bg=ui.control_active if ordering else ui.control_background,
                fg='#ffffff' if ordering else ui.accent_primary,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=ui.accent_primary if ordering else ui.border,
                highlightcolor=ui.accent_primary,
                font=("Sans", 11 if ordering else 10, "bold"),
                **size,
            )
            button._action_icon = icon
            button.bind('<Destroy>', lambda _event, widget=button: setattr(widget, '_action_icon', None))
            button.pack(side=tk.LEFT, padx=4)
            panel._poi_action_buttons.append(button)

    panel._refresh_poi_action_buttons()
    popup.update_idletasks()
    # Keep the footer visible with larger text or a wrapped business name.
    height = min(panel.winfo_screenheight() - 16, max(height, shell.winfo_reqheight() + 4))
    y = max(8, min(y, panel.winfo_screenheight() - height - 8))
    popup.geometry(f'{width}x{height}+{x}+{y}')
    popup.lift()
    popup.focus_force()
