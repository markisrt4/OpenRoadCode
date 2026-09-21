# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk widget construction helpers for the ORC navigation panel."""

import tkinter as tk

from controllers.poi import PoiCategory, TransitMode


def build_navigation_panel(panel) -> None:
    """Build the navigation panel widget hierarchy."""
    ui = panel._theme_bundle.ui
    panel.grid_rowconfigure(1, weight=1)
    panel.grid_rowconfigure(2, weight=0)
    panel.grid_columnconfigure(0, weight=1)
    bar = tk.Frame(
        self, bg=ui.surface_alt, height=38, highlightthickness=1, highlightbackground=ui.border
    )
    bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
    bar.grid_propagate(False)
    shortcuts = tk.Frame(bar, bg=ui.surface_alt)
    shortcuts.pack(side=tk.LEFT, padx=4, pady=3)
    for label, accent, key in (
        ("⌂ HOME", ui.accent_primary, "home"),
        ("▣ WORK", ui.accent_warning, "work"),
        ("⛽ GAS", ui.accent_danger, "gas"),
        ("▣ GROCERY", ui.accent_success, "grocery"),
        ("♨ FOOD", ui.accent_warning, "food"),
    ):
        tk.Button(
            shortcuts,
            text=label,
            command=lambda selected=key: panel._destination_shortcut(selected),
            bg=ui.control_background,
            fg=accent,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=ui.border,
            font=("Sans", 8, "bold"),
            width=9,
            height=1,
            padx=3,
            pady=1,
        ).pack(side=tk.LEFT, padx=(0, 4))
    transit = tk.Menubutton(
        shortcuts,
        text="▰ TRANSIT ▾",
        bg=ui.control_background,
        fg=ui.accent_primary,
        activebackground=ui.control_active,
        activeforeground="#ffffff",
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=ui.border,
        font=("Sans", 8, "bold"),
        width=11,
        height=1,
        padx=3,
        pady=1,
    )
    transit_menu = tk.Menu(transit, tearoff=False, bg=ui.control_background, fg=ui.control_text)
    for label, mode in (
        ("All transit", TransitMode.ALL),
        ("Bus", TransitMode.BUS),
        ("Rail", TransitMode.RAIL),
        ("Tram / Subway", TransitMode.TRAM_SUBWAY),
    ):
        transit_menu.add_command(
            label=label,
            command=lambda selected=mode: panel._start_poi_search(PoiCategory.TRANSIT, selected),
        )
    transit.configure(menu=transit_menu)
    transit.pack(side=tk.LEFT, padx=(0, 4))
    tk.Label(
        bar,
        textvariable=panel._shortcut_status,
        bg=ui.surface_alt,
        fg=ui.text_muted,
        font=("Sans", 7),
        anchor="e",
    ).pack(side=tk.RIGHT, padx=7)

    guidance = tk.Frame(
        self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border
    )
    guidance.grid(row=2, column=0, sticky="ew", pady=(4, 0))
    tk.Label(
        guidance,
        textvariable=panel._guidance_instruction,
        bg=ui.surface,
        fg=ui.text,
        font=("Sans", 10, "bold"),
        anchor="w",
    ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 6), pady=4)
    panel._clear_poi_button = tk.Button(
        guidance,
        text="CLEAR POIs",
        command=panel._clear_poi_search,
        bg=ui.control_background,
        fg=ui.text_muted,
        activebackground=ui.control_active,
        activeforeground="#ffffff",
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=ui.border,
        font=("Sans", 8, "bold"),
    )
    panel._clear_poi_button.pack(side=tk.RIGHT, padx=(4, 8), pady=3)

    panel._simulate_button = tk.Button(
        guidance,
        text="SIM DRIVE",
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
        text="CANCEL ROUTE",
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

    body = tk.Frame(self, bg=ui.background)
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
    panel._follow_button = panel._control(controls, "F", panel._toggle_follow, ui.accent_success)
    panel._follow_button.pack(fill=tk.X, padx=5, pady=(7, 5))
    panel.set_follow_enabled(panel._follow_enabled)
    pan = tk.Frame(controls, bg=ui.surface_alt)
    pan.pack(pady=2)
    for row, column, label, up, right in (
        (0, 1, "▲", 1, 0),
        (1, 0, "◀", 0, -1),
        (1, 2, "▶", 0, 1),
        (2, 1, "▼", -1, 0),
    ):
        tk.Button(
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
            font=("Sans", 9, "bold"),
            width=1,
            height=1,
            padx=2,
            pady=1,
        ).grid(row=row, column=column, padx=1, pady=1)
    panel._control(controls, "+", lambda: panel._change_zoom(1), ui.accent_primary).pack(
        fill=tk.X, padx=5, pady=2
    )
    tk.Label(
        controls,
        textvariable=panel._zoom_text,
        bg=ui.surface_alt,
        fg=ui.text,
        font=("Sans", 8, "bold"),
    ).pack(fill=tk.X, padx=5, pady=0)
    panel._control(controls, "−", lambda: panel._change_zoom(-1), ui.accent_primary).pack(
        fill=tk.X, padx=5, pady=2
    )
    for label, command, accent in (
        ("↗", lambda: panel._change_pitch(5), ui.accent_warning),
        ("↘", lambda: panel._change_pitch(-5), ui.accent_warning),
        ("N", panel._north_up, ui.text),
        ("◎", panel._recenter, ui.accent_success),
    ):
        panel._control(controls, label, command, accent).pack(fill=tk.X, padx=5, pady=2)
    tk.Label(
        controls,
        text="ZOOM\nTILT\nNORTH\nCENTER",
        bg=ui.surface_alt,
        fg=ui.text_muted,
        font=("Sans", 6),
        justify=tk.CENTER,
    ).pack(side=tk.BOTTOM, pady=5)


def show_poi_card(panel, poi) -> None:
    """Show selected business information above the native map window."""
    """Show selected business information above the native map window."""
    ui = panel._theme_bundle.ui
    if panel._poi_card is not None and panel._poi_card.winfo_exists():
        panel._poi_card.destroy()

    popup = tk.Toplevel(self)
    popup.title(poi.name)
    popup.configure(bg=ui.surface_alt)
    popup.transient(panel.winfo_toplevel())
    popup.resizable(False, False)
    popup.attributes("-topmost", True)
    panel._poi_card = popup

    width = 480
    height = 170
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

    tk.Label(
        frame,
        text=poi.name,
        bg=ui.surface_alt,
        fg=ui.text,
        font=("Sans", 15, "bold"),
    ).pack(pady=(14, 2))

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

    tk.Button(
        buttons,
        text="NAVIGATE",
        command=lambda: panel._navigate_to_poi(poi),
        bg=ui.control_background,
        fg=ui.accent_primary,
        activebackground=ui.control_active,
        activeforeground="#ffffff",
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=ui.border,
        font=("Sans", 10, "bold"),
        width=12,
        height=2,
    ).pack(side=tk.LEFT, padx=4)

    for action in poi.actions:
        if action.kind in {PoiActionKind.ORDER, PoiActionKind.OPEN_WEBSITE}:
            tk.Button(
                buttons,
                text=action.label,
                command=lambda selected=action: panel._execute_poi_action(poi, selected),
                bg=ui.control_background,
                fg=ui.accent_primary,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=ui.border,
                font=("Sans", 10, "bold"),
                width=12,
                height=2,
            ).pack(side=tk.LEFT, padx=4)

    tk.Button(
        buttons,
        text="CLOSE",
        command=popup.destroy,
        bg=ui.control_background,
        fg=ui.text_muted,
        activebackground=ui.control_active,
        activeforeground="#ffffff",
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=ui.border,
        font=("Sans", 8, "bold"),
        width=8,
    ).pack(side=tk.LEFT, padx=4)

    popup.lift()
    popup.focus_force()
