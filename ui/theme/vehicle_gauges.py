# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Theme values for the configurable vehicle instrument panel."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VehicleGaugeTheme:
    """Define shared colors for the vehicle instrument cluster."""

    face_color: str = "#f2efe5"
    face_shadow: str = "#9b9c99"
    background_color: str = "#090a0b"
    foreground_color: str = "#17191b"
    accent_color: str = "#d51f2b"
    muted_color: str = "#686b6d"
    bezel_dark: str = "#202326"
    bezel_mid: str = "#9da1a2"
    display_color: str = "#181b1c"
    display_text: str = "#ff694f"
    font_family: str = "DejaVu Sans"
    condensed_font_family: str = "DejaVu Sans Condensed"
    mono_font_family: str = "DejaVu Sans Mono"
    panel_background: str = "#000000"
    panel_foreground: str = "#ffffff"
    panel_status_disconnected: str = "#777777"
    panel_status_connected: str = "#d71920"
    bezel_outer: str = "#08090a"
    bezel_shadow: str = "#282b2d"
    bezel_metal_dark: str = "#707476"
    bezel_metal_light: str = "#e3e4e1"
    bezel_midlight: str = "#767a7c"
    bezel_inner: str = "#151719"
    face_highlight: str = "#ffffff"
    caution_color: str = "#e4a514"
    caution_tick_color: str = "#c88b0d"
    performance_label: str = "#8a8881"
    display_border: str = "#6f7373"
    needle_body: str = "#760d14"
    needle_outline: str = "#f26a70"
    hub_outer: str = "#202326"
    hub_metal: str = "#c7c9c7"
    hub_inner: str = "#2c2e2f"
    hub_center: str = "#dedfda"
    panel_inner: str = "#111315"
    panel_border: str = "#626668"
    panel_inner_border: str = "#2e3133"
    linear_card_background: str = "#24282b"
    linear_card_inner: str = "#111315"
    linear_card_border: str = "#858b8e"
    linear_card_highlight: str = "#3c4246"
    linear_card_text: str = "#f0f0ed"
    linear_card_muted: str = "#a9acad"
    primary_text: str = "#f0f0ed"
    normal_value: str = "#ffffff"
    caution_value: str = "#f0b323"
    danger_value: str = "#ff3446"
    disabled_normal_value: str = "#303234"
    disabled_caution_value: str = "#4e3d12"
    disabled_danger_value: str = "#57131b"
    marker_border: str = "#7b1017"
    threshold_marker: str = "#a92b34"
    endpoint_text: str = "#a9acad"
    metric_background: str = "#0a0c0d"
    metric_border: str = "#5e6263"
    metric_title: str = "#c8cbca"
    metric_unit: str = "#85898a"
    tire_background: str = "#090b0c"
    tire_title: str = "#d8dad9"
    vehicle_silhouette: str = "#1e2123"
    vehicle_silhouette_outline: str = "#747879"
    gear_background: str = "#08090a"
    gear_border: str = "#85898a"
    gear_title: str = "#d9dbd9"
    gear_active: str = "#ff3143"
    muted_detail: str = "#747879"
    diagnostics_background: str = "#0b0d0e"
    diagnostics_offline: str = "#777b7c"
    diagnostics_detail: str = "#aeb1b1"
    diagnostics_icon_active: str = "#ffb21a"
    diagnostics_icon_inactive: str = "#b7b9b8"


@dataclass(frozen=True, slots=True)
class VehicleGaugeRedlineTheme:
    """Configure the layered danger band on an intense round gauge."""

    shadow_color: str = "#650008"
    danger_color: str = "#e10d1c"
    highlight_color: str = "#ff4b56"
    numeral_color: str = "#c40012"
    shadow_radius_scale: float = 0.724
    danger_radius_scale: float = 0.705
    highlight_radius_scale: float = 0.681
    shadow_width_scale: float = 0.105
    danger_width_scale: float = 0.074
    highlight_width_scale: float = 0.022
    major_tick_width_scale: float = 0.043
    minor_tick_width_scale: float = 0.020

    def __post_init__(self) -> None:
        """Reject invisible or inverted redline geometry."""
        scales = (
            self.shadow_radius_scale,
            self.danger_radius_scale,
            self.highlight_radius_scale,
            self.shadow_width_scale,
            self.danger_width_scale,
            self.highlight_width_scale,
            self.major_tick_width_scale,
            self.minor_tick_width_scale,
        )
        if any(scale <= 0.0 for scale in scales):
            raise ValueError("redline geometry scales must be positive")


VEHICLE_GAUGE_THEME = VehicleGaugeTheme()
VEHICLE_GAUGE_REDLINE_THEME = VehicleGaugeRedlineTheme()
