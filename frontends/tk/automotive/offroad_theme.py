# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Resolved visual theme for the reusable off-road dashboard."""

from __future__ import annotations

from dataclasses import dataclass

from ui.theme import StyleSheet


@dataclass(frozen=True, slots=True)
class OffroadTheme:
    background: str
    panel: str
    border: str
    text: str
    muted: str
    primary: str
    success: str
    warning: str
    danger: str
    sky: str
    ground: str
    control_background: str
    control_active: str
    control_text: str

    @classmethod
    def from_style_sheet(cls, sheet: StyleSheet) -> "OffroadTheme":
        root = sheet.declarations(":root")
        values = sheet.declarations(".automotive-offroad")

        return cls(
            background=values.get("background", root["--background"]),
            panel=values.get("--panel", root["--surface"]),
            border=values.get("--border", root["--border"]),
            text=values.get("color", root["--text"]),
            muted=values.get("--muted", root["--text-muted"]),
            primary=values.get("--heading", root["--accent-primary"]),
            success=values.get("--success", root["--accent-success"]),
            warning=values.get("--warning", root["--accent-warning"]),
            danger=values.get("--danger", root["--accent-danger"]),
            sky=values.get("--sky", root["--surface"]),
            ground=values.get("--ground", root["--surface-alt"]),
            control_background=values.get(
                "--control-background",
                root["--control-background"],
            ),
            control_active=values.get(
                "--control-active",
                root["--control-active"],
            ),
            control_text=values.get(
                "--control-text",
                root["--control-text"],
            ),
        )
