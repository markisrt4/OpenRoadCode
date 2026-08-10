"""Car UI destination hosting the reusable vehicle gauges."""

from __future__ import annotations

import logging
from pathlib import Path

from controllers.automotive import VehicleStateSourceIf
from frontends.tk.automotive import VehicleGaugePanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.automotive import VehicleConnectionState

from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory


LOGGER = logging.getLogger(__name__)
DEFAULT_LAYOUT_PATH = Path.home() / ".config/openroadcode/vehicle_gauges.json"


class VehicleGaugesScreen(CarUiScreen):
    """Display vehicle gauges and optionally poll a telemetry source."""

    POLL_INTERVAL_MS = 250

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        create_menu_tile: MenuTileFactory,
        back_action,
        source: VehicleStateSourceIf | None = None,
        config_path: str | Path = DEFAULT_LAYOUT_PATH,
    ) -> None:
        super().__init__(host, ScreenId("vehicle_gauges"), create_menu_tile)
        self._back_action = back_action
        self._source = source
        self._config_path = config_path
        self._panel: VehicleGaugePanel | None = None
        self._callback_id: object | None = None
        self._connected = False
        self._visible = False

    def show(self) -> None:
        """Build the gauge panel and start its optional telemetry source."""
        self.prepare_screen("Vehicle Gauges", self._back_action)
        self._visible = True
        self._panel = VehicleGaugePanel(
            self.content_frame,
            config_path=self._config_path,
            columns=4,
        )
        self._panel.pack(fill="both", expand=True)
        self._panel.set_connection_state(VehicleConnectionState.DISCONNECTED)

        if self._source is None:
            self.set_status("Vehicle telemetry is not configured")
            return
        try:
            self._panel.set_connection_state(VehicleConnectionState.CONNECTING)
            self._source.connect()
        except Exception as exc:
            LOGGER.warning("Vehicle telemetry unavailable: %s", exc)
            self._panel.set_connection_state(VehicleConnectionState.ERROR)
            self.set_status("Vehicle telemetry unavailable")
            return
        self._connected = True
        self._panel.set_connection_state(VehicleConnectionState.CONNECTED)
        self.set_status("Vehicle telemetry connected")
        self._poll()

    def hide(self) -> None:
        """Stop updates and disconnect the optional telemetry source."""
        self._visible = False
        if self._callback_id is not None:
            try:
                self.host.cancel_ui_callback(self._callback_id)
            except Exception:
                pass
            self._callback_id = None
        if self._connected and self._source is not None:
            try:
                self._source.disconnect()
            except Exception:
                LOGGER.exception("Failed to disconnect vehicle telemetry")
        self._connected = False
        self._panel = None

    def _poll(self) -> None:
        self._callback_id = None
        if (
            not self._visible
            or self._panel is None
            or self._source is None
            or not self._connected
        ):
            return
        try:
            state = self._source.read_state()
        except Exception as exc:
            LOGGER.warning("Vehicle telemetry read failed: %s", exc)
            self._connected = False
            self._panel.set_connection_state(VehicleConnectionState.ERROR)
            self.set_status("Vehicle telemetry disconnected")
            return
        self._panel.update_state(state, connected=True)
        self._callback_id = self.host.schedule_ui_callback(
            self.POLL_INTERVAL_MS,
            self._poll,
        )
