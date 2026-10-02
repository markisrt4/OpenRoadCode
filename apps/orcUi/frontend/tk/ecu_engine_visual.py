# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Powertrain canvas rendering for the ECU dashboard."""

from __future__ import annotations

import math
import tkinter as tk

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from controllers.automotive import (
    EngineAnalysis,
    EngineLoadLevel,
    FuelControlMode,
    MixtureMode,
    TrackingQuality,
)
from ui.theme import ThemeBundle


def paint_engine_visual(
    canvas: tk.Canvas,
    summary_label: tk.Label,
    *,
    theme: ThemeBundle,
    vehicle_state: VehiclePresentationState,
    analysis: EngineAnalysis,
    animation_phase: float,
) -> None:
    """Render the ECU powertrain schematic and its interpretation summary."""
    state, ui = vehicle_state, theme.ui
    canvas.delete("all")
    w, h = max(260, canvas.winfo_width()), max(260, canvas.winfo_height())
    sx, sy = w / 400.0, h / 360.0

    def line(points, *, fill, width=5):
        canvas.create_line(
            *[v * (sx if i % 2 == 0 else sy) for i, v in enumerate(points)],
            fill=fill, width=width, smooth=True,
        )

    active = ui.accent_success
    intake = ui.accent_primary if analysis.engine_running else ui.text_muted
    fuel = "#D6A800" if analysis.engine_running else ui.text_muted
    combustion = "#D96A2B" if analysis.engine_running else ui.surface_alt
    exhaust = ui.accent_danger if analysis.engine_running else ui.text_muted
    turbo = ui.accent_primary if analysis.forced_induction_active else ui.text_muted

    # Turbo sits above the engine. Blue is the compressor/intake path;
    # red is the exhaust/turbine path. Both meet at the shared turbo shaft.
    turbo_x, turbo_y = 200, 70
    canvas.create_text(200*sx, 25*sy, text="TURBO", fill=turbo, font=("Sans", 8, "bold"))
    canvas.create_oval(174*sx, 44*sy, 226*sx, 96*sy, outline=turbo, width=5)
    cx, cy = turbo_x*sx, turbo_y*sy
    turbo_phase = animation_phase * math.tau
    for blade in range(5):
        angle = turbo_phase + blade * math.tau / 5.0
        canvas.create_line(
            cx, cy, cx + math.cos(angle)*16*sx, cy + math.sin(angle)*16*sy,
            fill=turbo, width=2,
        )
    canvas.create_oval(194*sx, 64*sy, 206*sx, 76*sy, fill=turbo, outline="")

    canvas.create_text(120*sx, 50*sy, text="INTAKE", fill=ui.text_muted, font=("Sans", 7, "bold"))
    line((112, 61, 145, 61, 174, 68), fill=intake, width=7)
    line((200, 96, 200, 110, 164, 122), fill=intake, width=7)
    if analysis.engine_running:
        for offset in (0.0, 0.34, 0.68):
            travel = (animation_phase + offset) % 1.0
            px = (116 + 55 * travel) * sx
            py = (61 + 7 * max(0.0, (travel - 0.55) / 0.45)) * sy
            canvas.create_oval(px-3, py-3, px+3, py+3, fill=intake, outline="")

    # Larger, centered engine now that the old left-side turbo no longer
    # consumes the composition.
    canvas.create_polygon(
        105*sx, 112*sy, 265*sx, 112*sy, 280*sx, 128*sy,
        274*sx, 158*sy, 95*sx, 158*sy, 89*sx, 130*sy,
        fill=ui.surface_alt, outline=intake, width=2,
    )
    canvas.create_text(185*sx, 136*sy, text="ENGINE", fill=ui.text, font=("Sans", 14, "bold"))
    canvas.create_polygon(
        97*sx, 158*sy, 274*sx, 158*sy, 286*sx, 205*sy,
        274*sx, 270*sy, 97*sx, 270*sy, 83*sx, 205*sy,
        fill=ui.surface_alt, outline=ui.border, width=2,
    )
    canvas.create_rectangle(105*sx, 160*sy, 265*sx, 190*sy, fill=ui.surface, outline=ui.border, width=1)

    line((115, 170, 255, 170), fill=fuel, width=5)
    canvas.create_text(185*sx, 164*sy, text="FUEL RAIL", fill=fuel, font=("Sans", 7, "bold"), anchor="s")
    cylinders = (120, 163, 207, 250)
    for x in cylinders:
        canvas.create_line(x*sx, 171*sy, x*sx, 195*sy, fill=fuel, width=3)
        canvas.create_polygon(
            (x-4)*sx, 192*sy, (x+4)*sx, 192*sy, x*sx, 201*sy,
            fill=fuel, outline="",
        )
        canvas.create_rectangle(
            (x-15)*sx, 199*sy, (x+15)*sx, 249*sy,
            fill=ui.surface, outline=ui.border, width=2,
        )
        glow = combustion if analysis.engine_running else ui.surface_alt
        canvas.create_oval(
            (x-10)*sx, 211*sy, (x+10)*sx, 231*sy,
            fill=glow, outline=ui.text_muted, width=1,
        )
        canvas.create_line(x*sx, 231*sy, x*sx, 257*sy, fill=ui.text_muted, width=2)

    # Keep the complete exhaust path outside the engine silhouette.
    # Runners leave the head to a right-side collector, feed the turbine,
    # then the turbine outlet descends through O2/catalyst to the tailpipe.
    collector_x, collector_y = 286, 190
    for index, x in enumerate(cylinders):
        runner_y = 190 + index * 8
        canvas.create_line(
            x*sx, 190*sy, 278*sx, runner_y*sy, collector_x*sx, collector_y*sy,
            fill=exhaust, width=2, smooth=True,
        )
    line((collector_x, collector_y, 304, 164, 304, 110, 224, 78), fill=exhaust, width=2)
    line((226, 72, 292, 76, 318, 96, 318, 282), fill=exhaust, width=3)
    canvas.create_text(326*sx, 190*sy, text="EXHAUST", anchor="w", fill=ui.text_muted, font=("Sans", 6, "bold"))
    if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP:
        canvas.create_oval(314*sx, 248*sy, 322*sx, 256*sy, fill=active, outline="")
        canvas.create_text(309*sx, 252*sy, text="O₂", anchor="e", fill=active, font=("Sans", 6, "bold"))

    # Compact accessory drive mounted against the bottom of the block.
    # The crank rotates smoothly with RPM while the cylinders remain still.
    crank_x, crank_y = 185, 266
    accessory_y = 257
    belt = ui.text_muted
    canvas.create_line(
        185*sx, crank_y*sy, 157*sx, accessory_y*sy,
        213*sx, accessory_y*sy, 185*sx, crank_y*sy,
        fill=belt, width=2, smooth=True,
    )
    for px, py, radius in ((157, accessory_y, 8), (213, accessory_y, 8), (crank_x, crank_y, 14)):
        canvas.create_oval(
            (px-radius)*sx, (py-radius)*sy, (px+radius)*sx, (py+radius)*sy,
            fill=ui.surface, outline=ui.border, width=2,
        )
    crank_phase = animation_phase * math.tau
    for blade in range(4):
        angle = crank_phase + blade * math.tau / 4.0
        canvas.create_line(
            crank_x*sx, crank_y*sy,
            (crank_x + math.cos(angle)*10)*sx,
            (crank_y + math.sin(angle)*10)*sy,
            fill=intake if analysis.engine_running else ui.text_muted, width=2,
        )
    for px, direction in ((157, -1.0), (213, 1.0)):
        angle = direction * crank_phase
        canvas.create_line(
            px*sx, accessory_y*sy,
            (px + math.cos(angle)*5)*sx,
            (accessory_y + math.sin(angle)*5)*sy,
            fill=ui.text_muted, width=2,
        )

    # Catalyst stays in the dedicated exhaust corridor, never crossing
    # the engine or accessory drive.
    canvas.create_polygon(
        306*sx, 280*sy, 312*sx, 275*sy, 324*sx, 275*sy, 330*sx, 280*sy,
        330*sx, 298*sy, 324*sx, 303*sy, 312*sx, 303*sy, 306*sx, 298*sy,
        fill=ui.surface_alt, outline=exhaust, width=1,
    )
    canvas.create_text(318*sx, 289*sy, text="CAT", fill=ui.text_muted, font=("Sans", 6, "bold"))
    line((318, 303, 318, 318, 292, 318), fill=exhaust, width=3)

    fuel_mode = "CLOSED LOOP" if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP else "OPEN LOOP" if analysis.fuel_control_mode is not FuelControlMode.UNKNOWN else "--"
    mixture = {
        MixtureMode.RICH: "RICH",
        MixtureMode.STOICHIOMETRIC: "STOICH",
        MixtureMode.LEAN: "LEAN",
        MixtureMode.UNKNOWN: "--",
    }[analysis.mixture_mode]
    load_text = {
        EngineLoadLevel.LOW: "LOW LOAD",
        EngineLoadLevel.MODERATE: "MODERATE LOAD",
        EngineLoadLevel.HIGH: "HIGH LOAD",
        EngineLoadLevel.UNKNOWN: "--",
    }[analysis.load_level]
    tracking = {
        TrackingQuality.GOOD: "TRACKING GOOD",
        TrackingQuality.MODERATE: "TRACKING MODERATE",
        TrackingQuality.POOR: "TRACKING POOR",
        TrackingQuality.UNKNOWN: "",
    }[analysis.mixture_tracking]
    summary = " · ".join(part for part in (fuel_mode, mixture, load_text, tracking) if part and part != "--")
    summary_label.configure(text=summary or "--")
