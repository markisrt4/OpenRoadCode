# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-specific assembly for the Car UI frontend."""
from __future__ import annotations
from apps.carUi.car_ui_dependencies import CarUiDependencies
from apps.carUi.car_ui_frontend_if import CarUiFrontendIf
from apps.carUi.car_ui_lifecycle import CarUiLifecycle
from apps.carUi.car_ui_router import CarUiRouter
from apps.carUi.car_ui_routes import register_car_ui_routes
from apps.carUi.position_status_presenter import PositionStatusPresenter
from apps.carUi.runtime.car_ui_input_runtime import CarUiInputRuntime
from apps.carUi.screens.car_ui_screen_factory_if import CarUiScreenFactoryIf
from apps.carUi.system import SystemControlManager, SystemController, VehicleStatusManager, VolumeManager
from input_events import InputDeviceId, InputDeviceType
from controllers.input import InputManager, InputMapper
from ui.screen_ui_if import ScreenUiIf
from ui.ui_action import UiAction

class CarUiComposition:
    def __init__(self, frontend: CarUiFrontendIf, dependencies: CarUiDependencies, screen_factory: CarUiScreenFactoryIf) -> None:
        self.frontend=frontend; self.dependencies=dependencies; self._screen_factory=screen_factory; self.screen_router=CarUiRouter(); self._active_screen: ScreenUiIf|None=None
        self._assemble_system_services(); self._assemble_screens(); self._assemble_input()
        register_car_ui_routes(self.screen_router, show_menu=frontend.show_menu, aircraft=self.aircraft_screen, weather=self.weather_screen, lighting=self.lighting_screen, fm_radio=self.fm_radio_screen, scanner_radio=self.scanner_screen, spotify=self.spotify_screen, netflix=self.netflix_screen, youtube=self.youtube_screen, music_visualizer=self.music_visualizer_screen, offroad_dashboard=self.offroad_dashboard_screen, vehicle_gauges=self.vehicle_gauges_screen)
    def _assemble_system_services(self)->None:
        f=self.frontend; d=self.dependencies
        self.system_controller=SystemController(remote_display=d.runtime.remote_display)
        self.vehicle_status_manager=VehicleStatusManager(top_bar_ui=f.top_bar, empty_value=f.empty_value)
        self.position_status_presenter=PositionStatusPresenter(source=d.position_source, dispatch=f.dispatch_ui, set_position=self.vehicle_status_manager.set_location, set_status=f.status_bar.set_status, on_position_state=d.navigation_controller.update_gps_state)
        self.volume_manager=VolumeManager(audio_controller=d.audio_controller, volume_ui=f.volume_panel, set_status=f.status_bar.set_status); f.volume_panel.set_volume_request_handler(self.volume_manager); self.volume_manager.refresh()
        self.system_control_manager=SystemControlManager(system_controller=self.system_controller, set_status=f.status_bar.set_status, request_close=f.close)
    def _assemble_screens(self)->None:
        s=self._screen_factory.create_screens(self.dependencies,self.vehicle_status_manager.set_frequency,self.frontend.dispatch_ui)
        self.aircraft_screen=s.aircraft; self.weather_screen=s.weather; self.lighting_screen=s.lighting; self.fm_radio_screen=s.fm_radio; self.scanner_screen=s.scanner; self.spotify_screen=s.spotify; self.netflix_screen=s.netflix; self.youtube_screen=s.youtube; self.music_visualizer_screen=s.music_visualizer; self.offroad_dashboard_screen=s.offroad_dashboard; self.vehicle_gauges_screen=s.vehicle_gauges
    def _assemble_input(self)->None:
        encoders=self.dependencies.rotary_encoders; encoder_ids=tuple(InputDeviceId(InputDeviceType.ROTARY_ENCODER,i) for i in range(len(encoders))); volume_index=self.dependencies.volume_encoder_index
        if not 0<=volume_index<len(encoder_ids): raise ValueError("volume_encoder_index must identify a configured encoder")
        volume_encoder_id=encoder_ids[volume_index]; user_encoder_ids=tuple(d for i,d in enumerate(encoder_ids) if i!=volume_index)
        self.input_manager=InputManager(mapper=InputMapper(user_encoder_id=user_encoder_ids, volume_encoder_id=volume_encoder_id, push_button_actions={InputDeviceId(InputDeviceType.PUSHBUTTON,i):UiAction[action.upper()] for i,action in enumerate(self.dependencies.push_button_actions)}), ui_handler=self.frontend)
        self.input_runtime=CarUiInputRuntime(dispatcher=self.frontend, encoders=encoders, device_ids=encoder_ids, input_handler=self.input_manager, keyboards=self.dependencies.keyboards, push_buttons=self.dependencies.push_buttons)
        self.lifecycle=CarUiLifecycle(position_presenter=self.position_status_presenter,input_runtime=self.input_runtime)
    def activate_screen(self,screen:ScreenUiIf|None)->None:
        if screen is self._active_screen:return
        previous=self._active_screen; self._active_screen=screen
        if previous is not None: previous.hide()
    def handle_ui_action(self,action:UiAction)->None:
        if self._active_screen is not None and self._active_screen.handle_ui_action(action):return
        if action is UiAction.VOLUME_UP:self.volume_manager.volume_up()
        elif action is UiAction.VOLUME_DOWN:self.volume_manager.volume_down()
        elif action is UiAction.VOLUME_MUTE:self.volume_manager.toggle_mute()
        elif action is UiAction.BACK:self.frontend.top_bar.invoke_back_action()
        elif action is UiAction.HOME:self.frontend.show_main_menu()
    def open_route(self,key:str)->None:self.screen_router.open(key)
    def has_route(self,key:str)->bool:return self.screen_router.contains(key)
