"""Configurable OpenRoadCode vehicle gauge subpanel."""

from __future__ import annotations

import json
import tkinter as tk
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING, Callable, Protocol

from round_gauge import (
    DiagnosticsPanel,
    GaugeStyle,
    GearIndicator,
    LinearGauge,
    MetricTile,
    RoundGauge,
    TirePressurePanel,
)

if TYPE_CHECKING:
    from controllers.automotive import VehicleState


@dataclass(frozen=True, slots=True)
class GaugeDefinition:
    """Maps one VehicleState field to a gauge presentation."""

    gauge_id: str
    title: str
    unit: str
    state_attribute: str
    minimum: float
    maximum: float
    major_step: float
    precision: int = 0
    shape: str = "round"
    value_scale: float = 1.0
    caution_low: float | None = None
    danger_low: float | None = None
    caution_high: float | None = None
    danger_high: float | None = None
    start_angle: float = 135.0
    sweep_angle: float = 270.0
    icon: str | None = None
    default_visible: bool = True


class GaugeWidget(Protocol):
    """Operations shared by both instrument shapes."""

    def set_value(self, value: object) -> None: ...

    def set_connected(self, connected: bool) -> None: ...


@dataclass(slots=True)
class GaugeLayoutItem:
    """Persisted visibility and ordering for one gauge."""

    gauge_id: str
    visible: bool = True


DEFAULT_GAUGES: tuple[GaugeDefinition, ...] = (
    GaugeDefinition(
        "rpm", "RPM", "x1000", "rpm", 0, 8, 1,
        precision=1, value_scale=0.001, caution_high=6.0, danger_high=6.5,
        start_angle=140, sweep_angle=260,
    ),
    GaugeDefinition(
        "boost", "Boost", "psi", "boost_psi", -15, 25, 5,
        precision=1, caution_high=15, danger_high=18,
        start_angle=140, sweep_angle=260,
    ),
    GaugeDefinition(
        "speed", "mp/h", "", "speed_mph", 0, 160, 20,
        start_angle=140, sweep_angle=260,
    ),
    GaugeDefinition(
        "gear", "Gear", "", "gear", 0, 6, 1, shape="gear",
    ),
    GaugeDefinition(
        "throttle", "Throttle", "%", "throttle_pct", 0, 100, 20,
        start_angle=140, sweep_angle=260,
    ),
    GaugeDefinition(
        "coolant", "Coolant", "°F", "coolant_temp_f", 100, 260, 20,
        shape="linear", caution_high=220, danger_high=240, icon="coolant",
    ),
    GaugeDefinition(
        "intake", "Intake Air", "°F", "intake_temp_f", 0, 180, 20,
        shape="linear", caution_high=130, danger_high=155,
    ),
    GaugeDefinition(
        "load", "Engine Load", "%", "engine_load_pct", 0, 100, 20,
        shape="linear", caution_high=80, danger_high=95,
    ),
    GaugeDefinition(
        "voltage", "Voltage", "V", "control_voltage", 8, 16, 1,
        precision=1, shape="linear",
        caution_low=12.0, danger_low=10.5, caution_high=14.8, danger_high=15.5,
        icon="voltage",
    ),
    GaugeDefinition(
        "fuel", "Fuel Level", "%", "fuel_level_pct", 0, 100, 20,
        shape="linear", caution_low=20, danger_low=8, icon="fuel",
    ),
    GaugeDefinition(
        "odometer", "Odometer", "mi", "odometer_miles", 0, 1_000_000, 10_000,
        shape="metric",
    ),
    GaugeDefinition(
        "trip", "Trip", "mi", "trip_miles", 0, 10_000, 100,
        precision=1, shape="metric",
    ),
    GaugeDefinition(
        "economy", "Fuel Economy", "mpg", "fuel_economy_mpg", 0, 100, 10,
        precision=1, shape="metric",
    ),
    GaugeDefinition(
        "range", "Estimated Range", "mi", "estimated_range_miles", 0, 1_000, 100,
        shape="metric",
    ),
    GaugeDefinition(
        "ambient", "Outside Air", "°F", "ambient_temp_f", -40, 140, 20,
        shape="metric",
    ),
    GaugeDefinition(
        "tires", "Tire Pressure", "psi", "tire_pressures_psi", 0, 60, 5,
        shape="tires",
    ),
    GaugeDefinition(
        "diagnostics", "Engine Diagnostics", "", "diagnostic_trouble_codes",
        0, 1, 1, shape="diagnostics",
    ),
)


class VehicleGaugeSubpanel(ttk.Frame):
    """Displays configurable gauges and accepts VehicleState updates."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        definitions: tuple[GaugeDefinition, ...] = DEFAULT_GAUGES,
        config_path: str | Path | None = None,
        columns: int = 3,
        show_config_button: bool = True,
    ) -> None:
        super().__init__(master)
        if columns < 1:
            raise ValueError("columns must be at least one")

        self._definitions = {item.gauge_id: item for item in definitions}
        self._config_path = Path(config_path).expanduser() if config_path else None
        self._preferred_columns = columns
        self._layout = self._load_layout(definitions)
        self._gauges: dict[str, GaugeWidget] = {}
        self._last_state: VehicleState | None = None
        self._connected = False
        self._style = GaugeStyle()

        self.configure(style="VehicleGauge.TFrame")
        self._configure_styles()

        self._toolbar = ttk.Frame(self, style="VehicleGauge.TFrame")
        self._toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        self._toolbar.columnconfigure(0, weight=1)

        self._status = ttk.Label(
            self._toolbar,
            text="VEHICLE DISCONNECTED",
            style="VehicleGaugeStatus.TLabel",
        )
        self._status.grid(row=0, column=0, sticky="w")

        if show_config_button:
            ttk.Button(
                self._toolbar,
                text="Arrange gauges",
                command=self.open_layout_editor,
            ).grid(row=0, column=1, sticky="e")

        self._gauge_host = tk.Frame(self, background=self._style.background_color)
        self._gauge_host.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.bind("<Configure>", self._on_panel_resize)

        self._rebuild_gauges()

    def update_state(self, state: VehicleState | None, *, connected: bool = True) -> None:
        """Update all gauges from a VehicleState snapshot."""
        self._last_state = state
        self._connected = connected
        self._status.configure(
            text="VEHICLE CONNECTED" if connected else "VEHICLE DISCONNECTED",
            style=(
                "VehicleGaugeConnected.TLabel"
                if connected
                else "VehicleGaugeStatus.TLabel"
            ),
        )
        for gauge_id, gauge in self._gauges.items():
            definition = self._definitions[gauge_id]
            if definition.shape == "diagnostics":
                codes = None if state is None else getattr(
                    state, "diagnostic_trouble_codes", None
                )
                mil_on = None if state is None else getattr(state, "mil_on", None)
                gauge.set_connected(connected)
                if isinstance(gauge, DiagnosticsPanel):
                    gauge.set_diagnostics(codes, mil_on)
                continue
            value = None if state is None else getattr(state, definition.state_attribute, None)
            if value is not None and definition.shape not in {
                "gear", "diagnostics", "tires"
            }:
                value = float(value) * definition.value_scale
            gauge.set_connected(connected)
            gauge.set_value(value)

    def set_gauge_visible(self, gauge_id: str, visible: bool) -> None:
        """Show or hide a gauge by its stable identifier."""
        item = self._layout_item(gauge_id)
        item.visible = visible
        self._persist_and_rebuild()

    def move_gauge(self, gauge_id: str, offset: int) -> None:
        """Move a gauge earlier or later in the configured order."""
        index = next(
            (position for position, item in enumerate(self._layout) if item.gauge_id == gauge_id),
            None,
        )
        if index is None:
            raise KeyError(gauge_id)
        destination = max(0, min(len(self._layout) - 1, index + offset))
        if destination == index:
            return
        item = self._layout.pop(index)
        self._layout.insert(destination, item)
        self._persist_and_rebuild()

    def open_layout_editor(self) -> None:
        """Open a modal-ish editor for visibility and gauge order."""
        editor = tk.Toplevel(self)
        editor.title("Arrange Vehicle Gauges")
        editor.configure(background="#000000")
        editor.transient(self.winfo_toplevel())
        editor.geometry("470x520")

        ttk.Label(
            editor,
            text="Gauge layout",
            style="VehicleGaugeHeading.TLabel",
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ttk.Label(
            editor,
            text="Enable gauges and move them into the order used by the panel.",
            style="VehicleGauge.TLabel",
        ).pack(anchor="w", padx=16, pady=(0, 10))

        list_host = ttk.Frame(editor, style="VehicleGauge.TFrame")
        list_host.pack(fill="both", expand=True, padx=16, pady=4)

        variables: dict[str, tk.BooleanVar] = {}
        selected_id = tk.StringVar(value=self._layout[0].gauge_id if self._layout else "")

        def render_rows() -> None:
            for child in list_host.winfo_children():
                child.destroy()
            for row_index, item in enumerate(self._layout):
                definition = self._definitions[item.gauge_id]
                variables.setdefault(item.gauge_id, tk.BooleanVar(value=item.visible))
                row = ttk.Frame(list_host, style="VehicleGauge.TFrame")
                row.grid(row=row_index, column=0, sticky="ew", pady=2)
                row.columnconfigure(1, weight=1)
                ttk.Radiobutton(
                    row,
                    variable=selected_id,
                    value=item.gauge_id,
                ).grid(row=0, column=0, padx=(0, 6))
                ttk.Checkbutton(
                    row,
                    text=f"{definition.title} ({definition.unit})",
                    variable=variables[item.gauge_id],
                ).grid(row=0, column=1, sticky="w")
                ttk.Label(
                    row,
                    text=str(row_index + 1),
                    style="VehicleGauge.TLabel",
                ).grid(row=0, column=2, padx=8)
            list_host.columnconfigure(0, weight=1)

        def move_selected(offset: int) -> None:
            gauge_id = selected_id.get()
            index = next(
                (i for i, item in enumerate(self._layout) if item.gauge_id == gauge_id),
                None,
            )
            if index is None:
                return
            destination = max(0, min(len(self._layout) - 1, index + offset))
            if destination != index:
                item = self._layout.pop(index)
                self._layout.insert(destination, item)
                render_rows()

        def apply() -> None:
            for item in self._layout:
                item.visible = variables[item.gauge_id].get()
            self._save_layout()
            self._rebuild_gauges()
            editor.destroy()

        render_rows()

        controls = ttk.Frame(editor, style="VehicleGauge.TFrame")
        controls.pack(fill="x", padx=16, pady=8)
        ttk.Button(controls, text="Move up", command=lambda: move_selected(-1)).pack(side="left")
        ttk.Button(controls, text="Move down", command=lambda: move_selected(1)).pack(side="left", padx=8)
        ttk.Button(controls, text="Cancel", command=editor.destroy).pack(side="right")
        ttk.Button(controls, text="Apply", command=apply).pack(side="right", padx=8)

        editor.grab_set()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.configure("VehicleGauge.TFrame", background="#000000")
        style.configure("VehicleGauge.TLabel", background="#000000", foreground="#ffffff")
        style.configure(
            "VehicleGaugeHeading.TLabel",
            background="#000000",
            foreground="#ffffff",
            font=("DejaVu Sans", 16, "bold"),
        )
        style.configure(
            "VehicleGaugeStatus.TLabel",
            background="#000000",
            foreground="#777777",
            font=("DejaVu Sans", 11, "bold"),
        )
        style.configure(
            "VehicleGaugeConnected.TLabel",
            background="#000000",
            foreground="#d71920",
            font=("DejaVu Sans", 11, "bold"),
        )

    def _load_layout(
        self,
        definitions: tuple[GaugeDefinition, ...],
    ) -> list[GaugeLayoutItem]:
        default = [
            GaugeLayoutItem(item.gauge_id, item.default_visible)
            for item in definitions
        ]
        if self._config_path is None or not self._config_path.exists():
            return default
        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8"))
            loaded = [GaugeLayoutItem(**item) for item in payload.get("gauges", [])]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return default

        known_ids = {item.gauge_id for item in definitions}
        result = [item for item in loaded if item.gauge_id in known_ids]
        existing = {item.gauge_id for item in result}
        result.extend(item for item in default if item.gauge_id not in existing)
        return result

    def _save_layout(self) -> None:
        if self._config_path is None:
            return
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"gauges": [asdict(item) for item in self._layout]}
        self._config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _persist_and_rebuild(self) -> None:
        self._save_layout()
        self._rebuild_gauges()

    def _layout_item(self, gauge_id: str) -> GaugeLayoutItem:
        for item in self._layout:
            if item.gauge_id == gauge_id:
                return item
        raise KeyError(gauge_id)

    def _rebuild_gauges(self) -> None:
        for child in self._gauge_host.winfo_children():
            child.destroy()
        self._gauges.clear()

        visible = [item for item in self._layout if item.visible]
        columns = self._effective_columns()
        for column in range(columns):
            self._gauge_host.columnconfigure(column, weight=1, uniform="gauge")

        row = 0
        column = 0
        for item in visible:
            definition = self._definitions[item.gauge_id]
            column_span = (
                2
                if definition.shape in {"linear", "diagnostics", "tires"}
                and columns > 1
                else 1
            )
            if column + column_span > columns:
                row += 1
                column = 0
            common_options = {
                "title": definition.title,
                "unit": definition.unit,
                "minimum": definition.minimum,
                "maximum": definition.maximum,
                "precision": definition.precision,
                "style": self._style,
            }
            if definition.shape == "linear":
                gauge = LinearGauge(
                    self._gauge_host,
                    caution_low=definition.caution_low,
                    danger_low=definition.danger_low,
                    caution_high=definition.caution_high,
                    danger_high=definition.danger_high,
                    icon=definition.icon,
                    **common_options,
                )
            elif definition.shape == "gear":
                gauge = GearIndicator(self._gauge_host, style=self._style)
            elif definition.shape == "metric":
                gauge = MetricTile(
                    self._gauge_host,
                    title=definition.title,
                    unit=definition.unit,
                    precision=definition.precision,
                    style=self._style,
                )
            elif definition.shape == "tires":
                gauge = TirePressurePanel(self._gauge_host, style=self._style)
            elif definition.shape == "diagnostics":
                gauge = DiagnosticsPanel(self._gauge_host, style=self._style)
            else:
                gauge = RoundGauge(
                    self._gauge_host,
                    major_step=definition.major_step,
                    caution_start=definition.caution_high,
                    danger_start=definition.danger_high,
                    start_angle=definition.start_angle,
                    sweep_angle=definition.sweep_angle,
                    size=220,
                    **common_options,
                )
            gauge.grid(
                row=row,
                column=column,
                columnspan=column_span,
                sticky="nsew" if definition.shape in {"round", "gear"} else "ew",
                padx=5,
                pady=5,
            )
            if definition.shape in {"round", "gear"}:
                self._gauge_host.rowconfigure(row, weight=1, minsize=190)
            elif definition.shape == "tires":
                self._gauge_host.rowconfigure(row, weight=0, minsize=170)
            else:
                self._gauge_host.rowconfigure(row, weight=0, minsize=112)
            self._gauges[item.gauge_id] = gauge
            column += column_span
            if column >= columns:
                row += 1
                column = 0

        if not visible:
            ttk.Label(
                self._gauge_host,
                text="No gauges are enabled. Use Arrange gauges to add one.",
                style="VehicleGauge.TLabel",
            ).grid(row=0, column=0, padx=20, pady=40)

        self.update_state(self._last_state, connected=self._connected)

    def _effective_columns(self) -> int:
        width = self.winfo_width()
        if width <= 1:
            return self._preferred_columns
        return max(1, min(self._preferred_columns, width // 210))

    def _on_panel_resize(self, _event: tk.Event[tk.Misc]) -> None:
        # Delay so repeated Configure events collapse into one layout pass.
        callback: Callable[[], None] = self._rebuild_if_column_count_changed
        pending = getattr(self, "_resize_after_id", None)
        if pending is not None:
            self.after_cancel(pending)
        self._resize_after_id = self.after(120, callback)

    def _rebuild_if_column_count_changed(self) -> None:
        self._resize_after_id = None
        current_columns = 0
        if self._gauges:
            current_columns = max(
                int(gauge.grid_info().get("column", 0))
                + int(gauge.grid_info().get("columnspan", 1))
                for gauge in self._gauges.values()
            )
        if current_columns != self._effective_columns():
            self._rebuild_gauges()
