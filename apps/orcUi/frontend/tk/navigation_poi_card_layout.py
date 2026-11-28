# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Build the selected POI card using the navigation panel's supplied toolkit."""

from ui.navigation.poi_models import PoiAction, PoiActionKind

from .navigation_earth_control import (
    build_earth_control,
    build_poi_icon_button,
    load_poi_action_icon,
)
from .navigation_poi_actions import request_poi_app_status
from .poi_app_indicator import PoiAppIndicator
from .poi_card_header import PoiCardHeader


def build_poi_card(panel, poi, tk) -> None:
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
    other_actions = tuple(
        action
        for action in poi.actions
        if action.kind
        in {PoiActionKind.ORDER, PoiActionKind.OPEN_WEBSITE, PoiActionKind.OPEN_ANDROID_APP}
        and action.provider_id != "google-earth-explore"
    )
    height = 330 if other_actions else 280
    has_waze = panel.__dict__.get("_waze_handler") is not None
    panel.update_idletasks()
    x = panel.winfo_rootx() + max(0, (panel.winfo_width() - width) // 2)
    y = panel.winfo_rooty() + max(0, (panel.winfo_height() - height) // 2)
    x = max(8, min(x, panel.winfo_screenwidth() - width - 8))
    y = max(8, min(y, panel.winfo_screenheight() - height - 8))
    popup.geometry(f"{width}x{height}+{x}+{y}")

    shell = tk.Frame(
        popup,
        bg=ui.surface_alt,
        highlightthickness=2,
        highlightbackground=ui.accent_primary,
    )
    shell.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

    panel._earth_button = None
    earth_action = next(
        (action for action in poi.actions if action.provider_id == "google-earth-explore"), None
    )

    details: list[str] = []
    if poi.brand and poi.brand.casefold() != poi.name.casefold():
        details.append(poi.brand)
    if poi.address:
        details.append(poi.address)
    elif poi.source_class == "saved-destination":
        details.append("Saved destination")
    else:
        details.append(poi.category.name.replace("_", " ").title())

    header = PoiCardHeader(
        shell,
        title=poi.name,
        details="  •  ".join(details),
        icon=poi.icon,
        theme=ui,
        title_style=poi.title_style,
    )
    header.pack(fill=tk.X)
    tk.Frame(shell, height=1, bg=ui.border).pack(fill=tk.X)
    frame = tk.Frame(shell, bg=ui.surface_alt, padx=12, pady=8)
    frame.pack(fill=tk.BOTH, expand=True)

    close_icon = load_poi_action_icon(frame, "close.png", tk).subsample(2, 2)
    close = tk.Button(
        frame,
        text="CLOSE",
        image=close_icon,
        compound=tk.LEFT,
        command=popup.destroy,
        bg=ui.control_background,
        fg=ui.text_muted,
        activebackground=ui.control_active,
        activeforeground=ui.text,
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=ui.border,
        highlightcolor=ui.accent_primary,
        font=("Sans", 10, "bold"),
        pady=6,
    )
    close._action_icon = close_icon
    close.bind("<Destroy>", lambda _event: setattr(close, "_action_icon", None))
    close.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    popup.bind("<Escape>", lambda _event: popup.destroy())

    buttons = tk.Frame(frame, bg=ui.surface_alt)
    buttons.pack()

    navigate = tk.Frame(buttons, bg=ui.surface_alt)
    navigate.pack(side=tk.LEFT, padx=(0, 8))
    tk.Label(
        navigate,
        text="NAVIGATE WITH",
        bg=ui.surface_alt,
        fg=ui.text_muted,
        font=("Sans", 8, "bold"),
    ).pack()
    nav_buttons = tk.Frame(navigate, bg=ui.surface_alt)
    nav_buttons.pack()
    build_poi_icon_button(
        panel, nav_buttons, "navigate.png", "ORC Map", lambda: panel._navigate_to_poi(poi), tk
    )
    panel._poi_action_buttons = []
    if has_waze:
        waze_button = build_poi_icon_button(
            panel,
            nav_buttons,
            "waze.png",
            "Waze",
            lambda: panel._navigate_to_poi_with_waze(poi),
            tk,
        )
        panel._poi_action_buttons.append(waze_button)
    explore = tk.Frame(buttons, bg=ui.surface_alt)
    explore.pack(side=tk.LEFT)
    local_action = next((a for a in poi.actions if a.kind is PoiActionKind.EXPLORE_3D), None)
    if earth_action is not None or local_action is not None:
        tk.Label(
            explore, text="EXPLORE", bg=ui.surface_alt, fg=ui.text_muted, font=("Sans", 8, "bold")
        ).pack()
    explore_buttons = tk.Frame(explore, bg=ui.surface_alt)
    explore_buttons.pack()
    if earth_action is not None:
        build_earth_control(panel, explore_buttons, poi, earth_action, tk)

    panel._local_3d_button = None
    if local_action is not None:
        panel._local_3d_button = build_poi_icon_button(
            panel,
            explore_buttons,
            "map_3d.png",
            "3D Map",
            lambda: panel._execute_poi_action(poi, local_action),
            tk,
        )
        panel._add_tooltip(
            panel._local_3d_button,
            "Offline 3D exploration; coverage depends on installed map packs",
        )

    extra_buttons = tk.Frame(frame, bg=ui.surface_alt)
    if other_actions:
        extra_buttons.pack(pady=(6, 0))
    for action in other_actions:
        if (
            action.kind
            in {PoiActionKind.ORDER, PoiActionKind.OPEN_WEBSITE, PoiActionKind.OPEN_ANDROID_APP}
            and action.provider_id != "google-earth-explore"
        ):
            ordering = action.kind is PoiActionKind.ORDER
            icon = load_poi_action_icon(extra_buttons, "order.png", tk) if ordering else None
            size = (
                {"width": 180, "height": 42, "padx": 12}
                if ordering
                else {"width": max(12, min(28, len(action.label) + 2)), "height": 2}
            )
            button = tk.Button(
                extra_buttons,
                text=action.label,
                image=icon if icon is not None else "",
                compound=tk.LEFT,
                state=tk.NORMAL if panel.online_actions_allowed else tk.DISABLED,
                disabledforeground=ui.text_muted,
                command=lambda selected=action: panel._execute_poi_action(poi, selected),
                bg=ui.control_active if ordering else ui.control_background,
                fg="#ffffff" if ordering else ui.accent_primary,
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
            button.bind(
                "<Destroy>", lambda _event, widget=button: setattr(widget, "_action_icon", None)
            )
            button.pack(side=tk.LEFT, padx=4)
            panel._poi_action_buttons.append(button)

    panel._poi_app_status_request = None
    panel._poi_app_indicator = None
    order = next((action for action in other_actions if action.kind is PoiActionKind.ORDER), None)
    if order is not None:
        store_action = PoiAction(
            PoiActionKind.OPEN_ANDROID_APP, "Google Play", provider_id=order.provider_id
        )
        indicator = PoiAppIndicator(
            frame,
            icon=poi.icon,
            theme=ui,
            open_store=lambda: panel._execute_poi_action(poi, store_action),
        )
        indicator.pack(pady=(6, 0))
        panel._poi_app_indicator = indicator
        panel._add_tooltip(
            indicator,
            "Ordering app: green check = installed; Play/download = not installed; Play/? = check unavailable. Click Play to open the app or its store listing. Globe = website only.",
        )
        request_poi_app_status(panel, poi, indicator)
        popup.bind(
            "<FocusIn>",
            lambda event: (
                request_poi_app_status(panel, poi, indicator)
                if event.widget is popup and indicator.winfo_exists()
                else None
            ),
            add="+",
        )

    panel._refresh_poi_action_buttons()
    popup.update_idletasks()
    # Keep the footer visible with larger text or a wrapped business name.
    height = min(panel.winfo_screenheight() - 16, max(height, shell.winfo_reqheight() + 4))
    y = max(8, min(y, panel.winfo_screenheight() - height - 8))
    popup.geometry(f"{width}x{height}+{x}+{y}")
    popup.lift()
    popup.focus_force()
