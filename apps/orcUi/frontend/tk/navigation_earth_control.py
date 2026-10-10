"""Compact, labelled icon actions inside the selected POI card."""

from pathlib import Path

_ASSETS = Path(__file__).with_name("assets")


def build_poi_icon_button(panel, parent, filename, label, command, toolkit):
    ui = panel._theme_bundle.ui
    icon = toolkit.PhotoImage(master=parent, file=str(_ASSETS / filename))
    button = toolkit.Button(
        parent, image=icon, text=label, compound=toolkit.TOP, command=command,
        bg=ui.surface_alt, activebackground=ui.control_active,
        fg=ui.accent_primary, disabledforeground=ui.text_muted,
        relief=toolkit.FLAT, borderwidth=0, highlightthickness=0,
        font=("Sans", 10, "bold"), padx=0, pady=2, width=88, height=72, takefocus=True)
    button._action_icon = icon
    button.pack(side=toolkit.LEFT, padx=4)
    return button


def build_earth_control(panel, parent, poi, action, toolkit) -> None:
    panel._earth_button = build_poi_icon_button(
        panel, parent, "earth.png", "Earth",
        lambda: panel._execute_poi_action(poi, action), toolkit)
    panel._earth_icon = panel._earth_button._action_icon
    panel._earth_offline_icon = toolkit.PhotoImage(master=parent, file=str(_ASSETS / "earth_offline.png"))
    panel._add_tooltip(panel._earth_button, "Explore this place in Google Earth (separate window)")
    panel._refresh_poi_action_buttons()
