"""Compact Earth link-out control above the native map client."""

from pathlib import Path

from frontends.x11.circular_window import shape_circle

_ASSETS = Path(__file__).with_name("assets")

def build_earth_overlay(panel, toolkit) -> None:
    ui = panel._theme_bundle.ui
    overlay = toolkit.Toplevel(panel, bg=ui.control_background)
    overlay.withdraw()
    overlay.overrideredirect(True)
    overlay.transient(panel.winfo_toplevel())
    panel._earth_overlay = overlay
    panel._earth_icon = toolkit.PhotoImage(master=overlay, file=str(_ASSETS / "earth.png"))
    panel._earth_offline_icon = toolkit.PhotoImage(master=overlay, file=str(_ASSETS / "earth_offline.png"))
    panel._earth_shape_applied = False
    panel._earth_button = toolkit.Button(
        overlay, image=panel._earth_icon, command=panel._explore_selected_place,
        bg=ui.control_background, activebackground=ui.control_active,
        relief=toolkit.FLAT, borderwidth=0, highlightthickness=0,
        padx=0, pady=0, width=46, height=46, takefocus=True)
    panel._earth_button.pack(fill="both", expand=True)
    panel._map_host.bind("<Configure>", lambda event: sync_earth_overlay(panel), add="+")
    panel._map_host.bind("<Map>", lambda event: sync_earth_overlay(panel), add="+")
    panel._map_host.bind("<Unmap>", lambda event: hide_earth_overlay(panel), add="+")
    panel._add_tooltip(panel._earth_button, "Open Google Earth (selected place, or Earth home; separate window)")
    panel._refresh_poi_action_buttons()


def sync_earth_overlay(panel) -> None:
    """Keep a separate X11 window above the renderer without global topmost."""
    overlay = panel.__dict__.get("_earth_overlay")
    if overlay is None or not overlay.winfo_exists():
        return
    host = panel._map_host
    if not host.winfo_viewable() or host.winfo_width() < 60:
        overlay.withdraw()
        return
    x = host.winfo_rootx() + host.winfo_width() - 54
    y = host.winfo_rooty() + 8
    overlay.geometry(f"46x46+{x}+{y}")
    overlay.deiconify()
    overlay.lift(panel.winfo_toplevel())
    if not panel._earth_shape_applied:
        overlay.update_idletasks()
        panel._earth_shape_applied = shape_circle(overlay.winfo_id(), 46)


def hide_earth_overlay(panel) -> None:
    overlay = panel.__dict__.get("_earth_overlay")
    if overlay is not None and overlay.winfo_exists():
        overlay.withdraw()
