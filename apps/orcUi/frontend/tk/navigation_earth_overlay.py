"""Compact Earth link-out control above the native map client."""

_GLOBE_XBM = '#define globe_width 24\n#define globe_height 24\nstatic unsigned char globe_bits[] = { 0x0, 0x0, 0x0, 0x0, 0x3c, 0x0, 0x80, 0xff, 0x1, 0xc0, 0x42, 0x3, 0x30, 0x42, 0xc, 0x10, 0x81, 0x8, 0xf8, 0xff, 0x1f, 0xfc, 0xff, 0x3f, 0x84, 0x0, 0x21, 0x84, 0x0, 0x21, 0x86, 0x0, 0x61, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x86, 0x0, 0x61, 0x84, 0x0, 0x21, 0x84, 0x0, 0x21, 0xfc, 0xff, 0x3f, 0xf8, 0xff, 0x1f, 0x10, 0x81, 0x8, 0x30, 0x42, 0xc, 0xc0, 0x42, 0x3, 0x80, 0xff, 0x1, 0x0, 0x3c, 0x0, 0x0, 0x0, 0x0 };'


def build_earth_overlay(panel, toolkit) -> None:
    ui = panel._theme_bundle.ui
    overlay = toolkit.Toplevel(panel, bg=ui.control_background)
    overlay.withdraw()
    overlay.overrideredirect(True)
    overlay.transient(panel.winfo_toplevel())
    panel._earth_overlay = overlay
    panel._earth_icon = toolkit.BitmapImage(master=overlay, data=_GLOBE_XBM,
                                            foreground=ui.accent_primary)
    panel._earth_button = toolkit.Button(
        overlay, image=panel._earth_icon, command=panel._explore_selected_place,
        bg=ui.control_background, activebackground=ui.control_active,
        relief=toolkit.FLAT, highlightthickness=1, highlightbackground=ui.border,
        width=40, height=40, takefocus=True)
    panel._earth_button.pack(fill="both", expand=True)
    panel._map_host.bind("<Configure>", lambda event: sync_earth_overlay(panel), add="+")
    panel._map_host.bind("<Map>", lambda event: sync_earth_overlay(panel), add="+")
    panel._map_host.bind("<Unmap>", lambda event: hide_earth_overlay(panel), add="+")
    panel._add_tooltip(panel._earth_button, "Explore the selected place in Google Earth (separate window)")
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


def hide_earth_overlay(panel) -> None:
    overlay = panel.__dict__.get("_earth_overlay")
    if overlay is not None and overlay.winfo_exists():
        overlay.withdraw()
