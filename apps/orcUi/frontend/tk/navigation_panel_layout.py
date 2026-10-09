# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk widget construction helpers for the ORC navigation panel."""

import tkinter as tk

from .navigation_earth_control import build_earth_control, build_poi_icon_button

from ui.navigation.poi_models import (PoiActionKind, PoiCategory, TransitMode)


def build_navigation_panel(panel) -> None:
    """Build the navigation panel widget hierarchy."""
    ui = panel._theme_bundle.ui
    panel.grid_rowconfigure(1, weight=1)
    panel.grid_rowconfigure(2, weight=0)
    panel.grid_columnconfigure(0, weight=1)
    bar = tk.Frame(
        panel, bg=ui.surface_alt, height=38, highlightthickness=1, highlightbackground=ui.border
    )
    bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
    bar.grid_propagate(False)
    shortcuts = tk.Frame(bar, bg=ui.surface_alt)
    shortcuts.pack(side=tk.LEFT, padx=4, pady=3)
    for label, accent, key in (
        ("⌂ Home", ui.accent_primary, "home"),
        ("▣ Work", ui.accent_warning, "work"),
    ):
        tk.Button(shortcuts, text=label,
                  command=lambda selected=key: panel._destination_shortcut(selected),
                  bg=ui.control_background, fg=accent, activebackground=ui.control_active,
                  activeforeground=ui.control_text, relief=tk.FLAT,
                  font=("Sans", 9, "bold"), padx=7, pady=3).pack(side=tk.LEFT, padx=(0, 4))
    places = tk.Menubutton(shortcuts, text="Places ▾", bg=ui.control_background,
                           fg=ui.text, relief=tk.FLAT, font=("Sans", 9, "bold"), padx=7, pady=3)
    places_menu = tk.Menu(places, tearoff=False, bg=ui.control_background, fg=ui.control_text)
    for label, key in (("Gas stations", "gas"), ("Groceries", "grocery"), ("Food", "food")):
        places_menu.add_command(label=label, command=lambda selected=key: panel._destination_shortcut(selected))
    transit_menu = tk.Menu(places_menu, tearoff=False, bg=ui.control_background, fg=ui.control_text)
    for label, mode in (("All transit", TransitMode.ALL), ("Bus", TransitMode.BUS),
                        ("Rail", TransitMode.RAIL), ("Tram / Subway", TransitMode.TRAM_SUBWAY)):
        transit_menu.add_command(label=label, command=lambda selected=mode: panel._start_poi_search(PoiCategory.TRANSIT, selected))
    places_menu.add_cascade(label="Transit", menu=transit_menu)
    places_menu.add_separator()
    places_menu.add_command(label="Clear place results", command=panel._clear_poi_search)
    panel._places_menu = places_menu
    places.configure(menu=places_menu)
    places.pack(side=tk.LEFT, padx=(0, 4))
    tk.Label(
        bar,
        textvariable=panel._shortcut_status,
        bg=ui.surface_alt,
        fg=ui.text_muted,
        font=("Sans", 7),
        anchor="w",
        wraplength=220,
        width=1,
    ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=7)

    panel._build_radar_controls(bar)

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
    controls = tk.Frame(
        body, bg=ui.surface_alt, width=62, highlightthickness=1, highlightbackground=ui.border
    )
    controls.grid(row=0, column=1, sticky="ns", padx=(4, 0))
    controls.grid_propagate(False)
    rail = tk.Frame(controls, bg=ui.surface_alt)
    rail.grid_propagate(False)
    rail.grid_columnconfigure(0, weight=1)
    for row, weight in ((0, 1), (1, 3), (2, 1), (4, 1), (5, 1)):
        rail.grid_rowconfigure(row, weight=weight, uniform="camera")
    orientation = tk.Frame(rail, bg=ui.surface_alt)
    orientation.grid(row=0, column=0, sticky="nsew", padx=3, pady=2)
    orientation.grid_propagate(False)
    orientation.grid_rowconfigure(0, weight=1)
    for column in range(3):
        orientation.grid_columnconfigure(column, weight=1, uniform="orientation")
    panel._follow_button = panel._control(orientation, "F", panel._toggle_follow, ui.accent_success)
    panel._follow_button.grid(row=0, column=0, sticky="nsew", padx=1)
    panel._add_tooltip(panel._follow_button, "Toggle following the vehicle")
    for column, label, command, accent, description in (
        (1, "N", panel._north_up, ui.text, "Rotate north to the top (turns follow off)"),
        (2, "◎", panel._recenter, ui.accent_success, "Center on the vehicle and resume following"),
    ):
        button = panel._control(orientation, label, command, accent)
        button.grid(row=0, column=column, sticky="nsew", padx=1)
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
            highlightthickness=1,
            highlightbackground=ui.border,
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
    panel._add_tooltip(zoom_in, "Zoom in")
    zoom_in.grid(row=0, column=0, sticky="nsew", padx=1)
    zoom_out = panel._control(zoom, "−", lambda: panel._change_zoom(-1), ui.accent_primary)
    panel._add_tooltip(zoom_out, "Zoom out")
    zoom_out.grid(row=0, column=1, sticky="nsew", padx=1)
    zoom_label = tk.Label(
        rail,
        textvariable=panel._zoom_text,
        bg=ui.surface_alt,
        fg=ui.text,
        font=("Sans", 8, "bold"),
    )
    zoom_label.grid(row=3, column=0, sticky="ew", padx=5)
    panel._add_tooltip(zoom_label, "Current map zoom level")
    dimension = tk.Frame(rail, bg=ui.surface_alt)
    dimension.grid(row=4, column=0, sticky="nsew", padx=4, pady=2)
    dimension.grid_propagate(False)
    dimension.grid_rowconfigure(0, weight=1)
    dimension.grid_columnconfigure(0, weight=1)
    dimension_button = panel._control(dimension, "", panel._toggle_map_dimension, ui.accent_primary)
    dimension_button.configure(textvariable=panel._dimension_text)
    dimension_button.grid(row=0, column=0, sticky="nsew")
    panel._add_tooltip(dimension_button, "Switch between overhead 2D and tilted 3D view")
    tilt = tk.Frame(rail, bg=ui.surface_alt)
    tilt.grid(row=5, column=0, sticky="nsew", padx=3, pady=2)
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

    # Seven button rows (including three pan rows), plus readout and group gaps.
    # Let grid divide a shorter viewport instead of packing controls off-screen.
    preferred_height = 7 * 44 + zoom_label.winfo_reqheight() + 20
    rail.place(x=1, y=1, relwidth=1, width=-2, height=preferred_height)
    controls.bind("<Configure>", lambda event: rail.place_configure(
        height=max(1, min(preferred_height, event.height - 2))
    ), add="+")


def show_poi_card(panel, poi) -> None:
    """Show selected business information above the native map window."""
    ui = panel._theme_bundle.ui
    if panel._poi_card is not None and panel._poi_card.winfo_exists():
        panel._poi_card.destroy()

    popup = tk.Toplevel(panel)
    popup.title(poi.name)
    popup.configure(bg=ui.surface_alt)
    popup.transient(panel.winfo_toplevel())
    popup.resizable(False, False)
    popup.attributes("-topmost", True)
    panel._poi_card = popup

    width = 480
    other_actions = tuple(action for action in poi.actions
                          if action.kind in {PoiActionKind.ORDER, PoiActionKind.OPEN_WEBSITE}
                          and action.provider_id != "google-earth-explore")
    height = 260 if other_actions else 210
    panel.update_idletasks()
    x = panel.winfo_rootx() + max(0, (panel.winfo_width() - width) // 2)
    y = panel.winfo_rooty() + max(0, (panel.winfo_height() - height) // 2)
    popup.geometry(f"{width}x{height}+{x}+{y}")

    frame = tk.Frame(
        popup,
        bg=ui.surface_alt,
        highlightthickness=2,
        highlightbackground=ui.accent_primary,
    )
    frame.pack(fill=tk.BOTH, expand=True)

    header = tk.Frame(frame, bg=ui.surface_alt)
    header.pack(fill=tk.X, pady=(10, 2))
    panel._earth_button = None
    earth_action = next((action for action in poi.actions
                         if action.provider_id == "google-earth-explore"), None)

    tk.Label(
        header,
        text=poi.name,
        bg=ui.surface_alt,
        fg=ui.text,
        font=("Sans", 15, "bold"),
        wraplength=350,
    ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

    details: list[str] = []
    if poi.brand and poi.brand.casefold() != poi.name.casefold():
        details.append(poi.brand)
    details.append(poi.category.name.replace("_", " ").title())

    tk.Label(
        frame,
        text="  •  ".join(details),
        bg=ui.surface_alt,
        fg=ui.text_muted,
        font=("Sans", 9),
    ).pack(pady=(0, 10))

    buttons = tk.Frame(frame, bg=ui.surface_alt)
    buttons.pack()

    build_poi_icon_button(panel, buttons, "navigate.png", "Navigate",
                          lambda: panel._navigate_to_poi(poi), tk)
    if earth_action is not None:
        build_earth_control(panel, buttons, poi, earth_action, tk)

    build_poi_icon_button(panel, buttons, "close.png", "Close", popup.destroy, tk)

    extra_buttons = tk.Frame(frame, bg=ui.surface_alt)
    if other_actions:
        extra_buttons.pack(pady=(6, 0))
    panel._poi_action_buttons = []
    for action in other_actions:
        if (action.kind in {PoiActionKind.ORDER, PoiActionKind.OPEN_WEBSITE}
                and action.provider_id != "google-earth-explore"):
            button = tk.Button(
                extra_buttons,
                text=action.label,
                state=tk.NORMAL if panel.online_actions_allowed else tk.DISABLED,
                disabledforeground=ui.text_muted,
                command=lambda selected=action: panel._execute_poi_action(poi, selected),
                bg=ui.control_background,
                fg=ui.accent_primary,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=ui.border,
                font=("Sans", 10, "bold"),
                width=max(12, min(28, len(action.label) + 2)),
                height=2,
            )
            button.pack(side=tk.LEFT, padx=4)
            panel._poi_action_buttons.append(button)

    panel._refresh_poi_action_buttons()
    popup.lift()
    popup.focus_force()
