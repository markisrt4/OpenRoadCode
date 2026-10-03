# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own forecast refresh workers independently of frontend widgets."""
from collections.abc import Callable
import threading
from controllers.weather.weather_controller import WeatherController
from ui.ui_dispatcher_if import UiDispatcherIf
from ui.weather.weather_ui_if import WeatherUiState
from controllers.weather.weather_presenter import WeatherPresenter
from ui.weather.weather_screen_ui_if import WeatherScreenRequestHandlerIf, WeatherScreenUiIf


class WeatherScreenController(WeatherScreenRequestHandlerIf):
    """Publish normalized forecasts and discard callbacks from hidden screens."""

    def __init__(
        self, dispatcher: UiDispatcherIf, controller: WeatherController,
        ui: WeatherScreenUiIf, on_weather_state: Callable[[WeatherUiState], None] | None = None,
    ):
        self._dispatcher = dispatcher
        self._controller = controller
        self._ui = ui
        self._presenter = WeatherPresenter(ui)
        self._on_weather_state = on_weather_state
        self._generation = 0
        self._visible = False
        self._closed = False

    def set_visible(self, visible: bool) -> None:
        """Update lifecycle. @param visible Whether the forecast screen is shown."""
        self._generation += 1
        self._visible = visible and not self._closed
        if self._visible:
            latest = self._controller.latest()
            if latest is not None:
                self._presenter.present(latest)
            self.request_refresh()

    def request_refresh(self) -> None:
        """Refresh the visible screen asynchronously."""
        if self._closed or not self._visible:
            return
        self._generation += 1
        generation = self._generation
        self._ui.set_loading(True)
        self._ui.set_weather_status("Weather: refreshing")
        threading.Thread(target=self._refresh, args=(generation,), daemon=True).start()

    def _refresh(self, generation):
        try:
            state = self._controller.refresh_if_stale(300.0)
            detail = ""
        except Exception as error:
            state, detail = None, str(error)
        self._dispatcher.schedule_ui_callback(0, lambda: self._complete(generation, state, detail))

    def _complete(self, generation, state, detail):
        if self._closed or not self._visible or generation != self._generation:
            return
        self._ui.set_loading(False)
        if state is not None:
            ui_state = self._presenter.present(state)
            if self._on_weather_state is not None:
                self._on_weather_state(ui_state)
        self._ui.set_weather_status(f"Weather: {detail}" if detail else "")

    def close(self):
        """Invalidate pending refresh callbacks and disconnect the view."""
        self._closed = True
        self.set_visible(False)
        self._ui.set_weather_request_handler(None)
