"""Car UI destination hosting the reusable Tk off-road dashboard."""

from __future__ import annotations

import logging

from controllers.navigation import NavigationControllerIf, NavigationStatePresenter
from frontends.tk.automotive import OffroadDashboardPanel
from ui.navigation import NavigationRequestHandlerIf
from ui.screen_ui_if import ScreenId
from ui.system import StatusMessage, StatusSeverity

from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from frontends.tk.tk_screen_host_if import TkScreenHostIf


LOGGER = logging.getLogger(__name__)


class OffroadDashboardScreen(CarUiScreen, NavigationRequestHandlerIf):
    """Host and refresh the off-road dashboard within Car UI navigation."""

    POLL_INTERVAL_MS = 75

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        controller: NavigationControllerIf,
        create_menu_tile: MenuTileFactory,
        back_action,
        pitch_warning_deg: float = 30.0,
        roll_warning_deg: float = 25.0,
    ) -> None:
        super().__init__(host, ScreenId("offroad_dashboard"), create_menu_tile)
        self._controller = controller
        self._back_action = back_action
        self._pitch_warning_deg = pitch_warning_deg
        self._roll_warning_deg = roll_warning_deg
        self._panel: OffroadDashboardPanel | None = None
        self._presenter: NavigationStatePresenter | None = None
        self._callback_id: object | None = None
        self._visible = False

    def show(self) -> None:
        """Build the panel and begin navigation updates."""
        self.prepare_screen("Off-Road", self._back_action)
        self._visible = True
        self._panel = OffroadDashboardPanel(
            self.content_frame,
            pitch_warning_deg=self._pitch_warning_deg,
            roll_warning_deg=self._roll_warning_deg,
            request_handler=self,
        )
        self._panel.pack(fill="both", expand=True)
        self._presenter = NavigationStatePresenter(
            orientation_ui=self._panel,
            translation_ui=self._panel,
            position_ui=self._panel,
            ground_track_ui=self._panel,
        )
        try:
            self._controller.start()
        except Exception as exc:
            LOGGER.warning("Motion sensor unavailable: %s", exc)
            self._panel.set_status(
                StatusMessage(
                    "Motion sensor unavailable",
                    StatusSeverity.ERROR,
                    source="navigation",
                )
            )
            self.set_status("Motion sensor unavailable")
            return
        self._panel.set_status("Navigation online")
        self.set_status("Off-road dashboard active")
        self._poll()

    def hide(self) -> None:
        """Stop polling and release the navigation sensor."""
        self._visible = False
        if self._callback_id is not None:
            try:
                self.host.cancel_ui_callback(self._callback_id)
            except Exception:
                pass
            self._callback_id = None
        try:
            self._controller.stop()
        except Exception:
            pass
        self._panel = None
        self._presenter = None

    def request_stationary_calibration(self) -> None:
        """Calibrate the active navigation controller."""
        if self._panel is None or not self._controller.is_started:
            return
        self._panel.set_status("Calibrating · keep vehicle still")
        try:
            result = self._controller.calibrate_stationary()
        except Exception as exc:
            LOGGER.warning("Navigation calibration failed: %s", exc)
            self._panel.set_status(
                StatusMessage(
                    "Calibration error",
                    StatusSeverity.ERROR,
                    source="navigation",
                )
            )
        else:
            self._panel.set_status(f"Calibrated · {result.sample_count} samples")

    def request_heading_reset(self) -> None:
        """Reset the active relative-heading estimate."""
        if self._panel is None or not self._controller.is_started:
            return
        self._controller.reset_heading()
        self._panel.set_status("Relative heading zeroed")

    def _poll(self) -> None:
        self._callback_id = None
        if not self._visible or self._panel is None or self._presenter is None:
            return
        try:
            state = self._controller.read_state()
        except Exception as exc:
            LOGGER.warning("Navigation read failed: %s", exc)
            self._panel.set_status(
                StatusMessage(
                    "Navigation error",
                    StatusSeverity.ERROR,
                    source="navigation",
                )
            )
            return
        self._presenter.present(state)
        if self._controller.calibration is None:
            self._panel.set_status("Navigation online · calibration recommended")
        else:
            self._panel.set_status("Navigation online · calibrated")
        self._callback_id = self.host.schedule_ui_callback(
            self.POLL_INTERVAL_MS,
            self._poll,
        )
