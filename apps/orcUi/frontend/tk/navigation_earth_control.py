"""Compact destination exploration control inside the selected POI card."""

from pathlib import Path

_ASSETS = Path(__file__).with_name("assets")


def build_earth_control(panel, parent, poi, action, toolkit) -> None:
    ui = panel._theme_bundle.ui
    panel._earth_icon = toolkit.PhotoImage(master=parent, file=str(_ASSETS / "earth.png"))
    panel._earth_offline_icon = toolkit.PhotoImage(master=parent, file=str(_ASSETS / "earth_offline.png"))
    panel._earth_button = toolkit.Button(
        parent, image=panel._earth_icon,
        command=lambda: panel._execute_poi_action(poi, action),
        bg=ui.surface_alt, activebackground=ui.surface_alt,
        relief=toolkit.FLAT, borderwidth=0, highlightthickness=0,
        padx=0, pady=0, width=46, height=46, takefocus=True)
    panel._earth_button.pack(side=toolkit.RIGHT, padx=(8, 12))
    panel._add_tooltip(panel._earth_button, "Explore this place in Google Earth (separate window)")
    panel._refresh_poi_action_buttons()
