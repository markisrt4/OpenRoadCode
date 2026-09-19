# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level composition for the complete ORC UI application."""

from __future__ import annotations

from dataclasses import dataclass

from apps.orcUi.application_runtime import OrcUiApplicationRuntime, create_orc_ui_application_runtime
from apps.orcUi.composition.core import CoreComposition, create_core_composition
from apps.orcUi.composition.games import configure_games
from apps.orcUi.composition.media import MediaComposition, configure_media
from apps.orcUi.composition.radio import RadioComposition, configure_radio
from apps.orcUi.frontend.tk.home_screen import HomeScreen
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.offroad_screen import OffRoadScreen
from apps.orcUi.frontend.tk.settings_screen import SettingsScreen
from apps.orcUi.frontend.tk.vehicle_screen import VehicleScreen
from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.games import GamesScreen


@dataclass(slots=True)
class OrcUiComposition:
    """Own every top-level object created for one ORC UI process."""

    core: CoreComposition
    runtime: OrcUiApplicationRuntime
    radio: RadioComposition
    media: MediaComposition
    games: GamesScreen
    home: HomeScreen | None = None
    navigation: NavigationScreen | None = None
    vehicle: VehicleScreen | None = None
    offroad: OffRoadScreen | None = None
    settings: SettingsScreen | None = None

    @property
    def app(self) -> OrcUiApp:
        return self.core.app

    def run(self) -> None:
        """Run Tk, close every owned resource, then honor host lifecycle intent."""
        try:
            self.app.schedule_ui_callback(1500, self.runtime.start_background_apps)
            self.core.start()
            self.app.run()
        finally:
            try:
                self.games.shutdown()
            finally:
                try:
                    self.media.close()
                finally:
                    try:
                        self.core.close()
                    finally:
                        self.runtime.close()

        self.core.lifecycle.execute_requested_action()


def create_orc_ui_composition() -> OrcUiComposition:
    """Create all shell, runtime, and feature dependencies in one place."""
    runtime = create_orc_ui_application_runtime()
    core: CoreComposition | None = None
    try:
        core = create_core_composition()
        app = core.app
        app.set_theme_change_handler(core.map_runtime.set_theme)
        radio = configure_radio(app, runtime)
        games = configure_games(app)
        media = configure_media(app, runtime)
        def navigate_home_context(name: str) -> None:
            context_name = name.strip().upper()
            if not context_name:
                raise ValueError("Context destination must not be empty")
            if context_name == "TRIP":
                app.navigate_to("VEHICLE")
                vehicle.show_trip_view()
            elif context_name in {"VEHICLE", "OFF-ROAD"}:
                app.navigate_to(context_name)
            else:
                app.navigate_to(context_name)

        home = HomeScreen(
            app,
            map_runtime=core.map_runtime,
            map_request_handler=core.map_camera.request_handler,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            presentation=core.presentation,
            telemetry_profile_request=core.telemetry_profile_request,
            on_expand_context=navigate_home_context,
        )
        navigation = NavigationScreen(
            app,
            map_runtime=core.map_runtime,
            map_request_handler=core.map_camera.request_handler,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            telemetry_profile_request=core.telemetry_profile_request,
            on_back=lambda: app.navigate_to("HOME"),
        )
        vehicle = VehicleScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            presentation=core.presentation,
            telemetry_profile_request=core.telemetry_profile_request,
            vehicle_configuration=lambda: core.vehicle_configuration.configuration,
            on_back=lambda: app.navigate_to("HOME"),
        )
        offroad = OffRoadScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            presentation=core.presentation,
            on_back=lambda: app.navigate_to("HOME"),
        )
        settings = SettingsScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            telemetry_profile_request=core.telemetry_profile_request,
            vehicle_configuration=lambda: core.vehicle_configuration.configuration,
            on_vehicle_configuration_changed=core.vehicle_configuration.update,
            on_back=lambda: app.navigate_to("HOME"),
        )
        home.set_radio_factory(radio.home_factory)
        home.set_media_factory(media.home_factory)
        core.presentation.observe_vehicle(home.apply_vehicle_state)
        core.presentation.observe_trip(home.apply_trip_state)
        core.presentation.observe_position(home.apply_position_state)
        core.presentation.observe_attitude(home.apply_attitude_state)
        core.presentation.observe_vehicle(vehicle.apply_vehicle_state)
        core.presentation.observe_trip(vehicle.apply_trip_state)
        core.presentation.observe_engine_analysis(vehicle.apply_engine_analysis)
        core.presentation.observe_position(vehicle.apply_position_state)
        core.presentation.observe_attitude(vehicle.apply_attitude_state)
        core.presentation.observe_position(offroad.apply_position_state)
        core.presentation.observe_attitude(offroad.apply_attitude_state)
        core.vehicle_configuration.observe(vehicle.set_vehicle_configuration)
        app.register_screen("HOME", home)
        app.register_screen("NAVIGATION", navigation)
        app.register_screen("VEHICLE", vehicle)
        app.register_screen("OFF-ROAD", offroad, show_in_navigation=False)
        app.register_screen("SETTINGS", settings, show_in_navigation=False)
    except Exception:
        if core is not None:
            core.close()
        runtime.close()
        raise
    return OrcUiComposition(
        core=core,
        runtime=runtime,
        radio=radio,
        media=media,
        games=games,
        home=home,
        navigation=navigation,
        vehicle=vehicle,
        offroad=offroad,
        settings=settings,
    )
