# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-specific assembly for the Car UI frontend."""

from __future__ import annotations

from apps.carUi.bus_position_presenter import BusPositionPresenter
from apps.carUi.car_ui_dependencies import CarUiDependencies
from apps.carUi.car_ui_frontend_if import CarUiFrontendIf
from apps.carUi.car_ui_lifecycle import CarUiLifecycle
from apps.carUi.car_ui_router import CarUiRouter
from apps.carUi.car_ui_routes import register_car_ui_routes
from apps.carUi.runtime.car_ui_input_runtime import CarUiInputRuntime
from apps.carUi.screens.car_ui_screen_factory_if import CarUiScreenFactoryIf
from apps.carUi.system import SystemControlManager, SystemController, VehicleStatusManager, VolumeManager
from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.input import InputManager, InputMapper
from input_events import InputDeviceId, InputDeviceType
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    decode_attitude_state,
    decode_imu_state,
    decode_motion_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from ui.screen_ui_if import ScreenId, ScreenUiIf
from ui.ui_action import UiAction


class CarUiComposition:
    """Construct and connect screens, presenters, managers, and routes."""

    def __init__(self, frontend: CarUiFrontendIf, dependencies: CarUiDependencies, screen_factory: CarUiScreenFactoryIf) -> None:
        self.frontend = frontend
        self.dependencies = dependencies
        self._screen_factory = screen_factory
        self.screen_router = CarUiRouter()
        self._active_screen: ScreenUiIf | None = None
        self._assemble_system_services()
        self._assemble_screens()
        self._assemble_message_bus()
        self._assemble_input()
        register_car_ui_routes(self.screen_router, show_menu=frontend.show_menu, aircraft=self.aircraft_screen, weather=self.weather_screen, lighting=self.lighting_screen, fm_radio=self.fm_radio_screen, scanner_radio=self.scanner_screen, spotify=self.spotify_screen, netflix=self.netflix_screen, youtube=self.youtube_screen, offroad_dashboard=self.offroad_dashboard_screen, vehicle_gauges=self.vehicle_gauges_screen)

    def _assemble_system_services(self) -> None:
        frontend = self.frontend
        dependencies = self.dependencies
        self.system_controller = SystemController(remote_display=dependencies.runtime.remote_display)
        self.vehicle_status_manager = VehicleStatusManager(top_bar_ui=frontend.top_bar, empty_value=frontend.empty_value)
        self.bus_position_presenter = BusPositionPresenter(
            set_position=self.vehicle_status_manager.set_location,
            set_status=frontend.status_bar.set_status,
        )
        self.volume_manager = VolumeManager(audio_controller=dependencies.audio_controller, volume_ui=frontend.volume_panel, set_status=frontend.status_bar.set_status)
        frontend.volume_panel.set_volume_request_handler(self.volume_manager)
        self.volume_manager.refresh()
        self.system_control_manager = SystemControlManager(system_controller=self.system_controller, set_status=frontend.status_bar.set_status, request_close=frontend.close)

    def _assemble_screens(self) -> None:
        screens = self._screen_factory.create_screens(self.dependencies, self.vehicle_status_manager.set_frequency, self.frontend.dispatch_ui)
        self.aircraft_screen = screens.aircraft
        self.weather_screen = screens.weather
        self.lighting_screen = screens.lighting
        self.fm_radio_screen = screens.fm_radio
        self.scanner_screen = screens.scanner
        self.spotify_screen = screens.spotify
        self.netflix_screen = screens.netflix
        self.youtube_screen = screens.youtube
        self.offroad_dashboard_screen = screens.offroad_dashboard
        self.vehicle_gauges_screen = screens.vehicle_gauges

    def _assemble_message_bus(self) -> None:
        """Route public telemetry contracts into Tk screens on the UI thread."""
        def bus_error(topic: str, error: Exception) -> None:
            self.frontend.dispatch_ui(lambda: self._apply_bus_error(topic, error))

        config = ServiceRuntimeConfigParser(self.dependencies.runtime.config_path).load()
        self.message_dispatcher = MessageDispatcher(
            ZeroMqSubscriber(config.messaging.subscriber_endpoint),
            error_handler=bus_error,
        )
        registrations = (
            (VEHICLE_STATE_TOPIC, decode_vehicle_state, self.vehicle_gauges_screen.set_vehicle_message),
            (ATTITUDE_STATE_TOPIC, decode_attitude_state, self.offroad_dashboard_screen.set_attitude_message),
            (IMU_STATE_TOPIC, decode_imu_state, self.offroad_dashboard_screen.set_imu_message),
            (POSITION_STATE_TOPIC, decode_position_state, self._set_position_message),
            (MOTION_STATE_TOPIC, decode_motion_state, self.offroad_dashboard_screen.set_motion_message),
        )
        for topic, decoder, handler in registrations:
            self.message_dispatcher.register(topic, decoder, lambda message, callback=handler: self.frontend.dispatch_ui(lambda: callback(message)))

    def _set_position_message(self, message) -> None:
        self.bus_position_presenter.set_position_message(message)
        self.offroad_dashboard_screen.set_position_message(message)

    def _apply_bus_error(self, topic: str, error: Exception) -> None:
        if topic == VEHICLE_STATE_TOPIC:
            self.vehicle_gauges_screen.set_vehicle_error(topic, error)
        else:
            if topic == POSITION_STATE_TOPIC or topic == "receive":
                self.bus_position_presenter.set_error()
            self.offroad_dashboard_screen.set_navigation_error(topic, error)

    def _assemble_input(self) -> None:
        encoders = self.dependencies.rotary_encoders
        encoder_ids = tuple(InputDeviceId(InputDeviceType.ROTARY_ENCODER, index) for index in range(len(encoders)))
        volume_index = self.dependencies.volume_encoder_index
        if not 0 <= volume_index < len(encoder_ids):
            raise ValueError("volume_encoder_index must identify a configured encoder")
        volume_encoder_id = encoder_ids[volume_index]
        user_encoder_ids = tuple(device_id for index, device_id in enumerate(encoder_ids) if index != volume_index)
        self.input_manager = InputManager(mapper=InputMapper(user_encoder_id=user_encoder_ids, volume_encoder_id=volume_encoder_id, push_button_actions={InputDeviceId(InputDeviceType.PUSHBUTTON, index): UiAction[action.upper()] for index, action in enumerate(self.dependencies.push_button_actions)}), ui_handler=self.frontend)
        self.input_runtime = CarUiInputRuntime(dispatcher=self.frontend, encoders=encoders, device_ids=encoder_ids, input_handler=self.input_manager, keyboards=self.dependencies.keyboards, push_buttons=self.dependencies.push_buttons)
        self.lifecycle = CarUiLifecycle(input_runtime=self.input_runtime, message_dispatcher=self.message_dispatcher)

    def activate_screen(self, screen: ScreenUiIf | None) -> None:
        if screen is self._active_screen:
            return
        previous = self._active_screen
        self._active_screen = screen
        if previous is not None:
            previous.hide()

    def handle_ui_action(self, action: UiAction) -> None:
        if self._active_screen is not None and self._active_screen.handle_ui_action(action):
            return
        if action is UiAction.VOLUME_UP:
            self.volume_manager.volume_up()
        elif action is UiAction.VOLUME_DOWN:
            self.volume_manager.volume_down()
        elif action is UiAction.VOLUME_MUTE:
            self.volume_manager.toggle_mute()
        elif action is UiAction.BACK:
            self.frontend.top_bar.invoke_back_action()
        elif action is UiAction.HOME:
            self.frontend.show_main_menu()

    def open_route(self, key: str) -> None:
        self.screen_router.open(key)

    def has_route(self, key: str) -> bool:
        return self.screen_router.contains(key)
