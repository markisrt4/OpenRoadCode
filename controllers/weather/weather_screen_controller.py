# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own forecast refresh workers independently of frontend widgets."""
from common.resource_cleanup import close_resources
from collections.abc import Callable
import threading
import time
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
        *, online_allowed: Callable[[], bool] = lambda: True,
    ):
        self._dispatcher = dispatcher
        self._controller = controller
        self._ui = ui
        self._presenter = WeatherPresenter(ui)
        self._on_weather_state = on_weather_state
        self._generation = 0
        self._visible = False
        self._closed = False
        self._clock = time.time
        self._last_state = None
        self._last_error = ""
        self._stale_refresh = False
        self._online_allowed = online_allowed
        self._unsubscribe_mode = lambda: None

    def set_visible(self, visible: bool) -> None:
        """Update lifecycle. @param visible Whether the forecast screen is shown."""
        self._generation += 1
        self._visible = visible and not self._closed
        if self._visible:
            latest = self._controller.latest()
            if latest is not None:
                self._last_state = latest
                self._presenter.present(latest)
            self._ui.set_online(self._online_allowed())
            self.request_refresh(force=False)

    def bind_online_mode(self, mode) -> None:
        """Observe backend connectivity. @param mode Connectivity mode source."""
        self._unsubscribe_mode()
        self._unsubscribe_mode = mode.subscribe(self.mode_changed)
        self.mode_changed(mode.online)

    def mode_changed(self, online: bool) -> None:
        """Invalidate old work. @param online Effective connectivity."""
        if self._closed:
            return
        self._generation += 1
        self._ui.set_online(online)
        if self._visible:
            self._ui.set_loading(False)
            if online:
                self.request_refresh(force=True)
            else:
                self._ui.set_weather_status('Offline mode: cached weather; alerts may be outdated')

    def request_refresh(self, *, force: bool = True) -> None:
        """Refresh the visible screen asynchronously."""
        if self._closed or not self._visible:
            return
        if not self._online_allowed():
            self._ui.set_loading(False)
            self._ui.set_weather_status('Offline mode: cached weather; alerts may be outdated')
            return
        self._generation += 1
        generation = self._generation
        self._ui.set_loading(True)
        self._ui.set_weather_status("Weather: refreshing")
        threading.Thread(target=self._refresh, args=(generation, force), daemon=True).start()

    def _refresh(self, generation, force=False):
        try:
            state = (self._controller.refresh() if force else self._controller.refresh_if_stale(300.0))
            detail = ""
        except Exception as error:
            state, detail = None, str(error)
        self._dispatcher.dispatch_ui(lambda: self._complete(generation, state, detail))

    def _complete(self, generation, state, detail):
        if self._closed or not self._visible or generation != self._generation:
            return
        self._ui.set_loading(False)
        if state is not None:
            self._last_state = state
            ui_state = self._presenter.present(state)
            if self._on_weather_state is not None:
                self._on_weather_state(ui_state)
        self._last_error = detail
        self._stale_refresh = state is not None and self._clock() - state.fetched_at > 300
        self._monitor_status(generation)

    def _monitor_status(self, generation):
        if self._closed or not self._visible or generation != self._generation:
            return
        state = self._last_state
        age = max(1, int((self._clock() - state.fetched_at) / 60)) if state is not None else 0
        if self._last_error and state is None:
            status = f"Weather unavailable: {self._last_error}"
        elif self._last_error or self._stale_refresh:
            status = f"Weather: showing saved data ({age} min old); refresh unavailable"
        elif state is not None and self._clock() - state.fetched_at > 300:
            status = f"Weather: data is {age} min old; refresh to update"
        else:
            status = ""
        self._ui.set_weather_status(status)
        if state is not None:
            self._dispatcher.schedule_ui_callback(60000, lambda: self._monitor_status(generation))

    def close(self):
        """Invalidate pending refresh callbacks and disconnect the view."""
        if self._closed:
            return
        self._closed = True
        close_resources(self._unsubscribe_mode, lambda: self.set_visible(False),
                        lambda: self._ui.set_weather_request_handler(None))
