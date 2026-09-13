# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for shell/map/volume/state-ingress composition."""

import math
import unittest
from unittest.mock import Mock, patch

from apps.orcUi.composition.core import CoreComposition, create_core_composition


class CoreCompositionTest(unittest.TestCase):
    def test_lifecycle_refreshes_volume_starts_ingress_and_closes_map(self) -> None:
        app = Mock()
        map_runtime = Mock()
        map_camera = Mock()
        ingress = Mock()
        trip_runtime = Mock()
        trip_publisher = Mock()
        lifecycle = Mock()
        volume = Mock()
        core = CoreComposition(
            app=app,
            map_runtime=map_runtime,
            map_camera=map_camera,
            state_ingress=ingress,
            trip_runtime=trip_runtime,
            trip_publisher=trip_publisher,
            lifecycle=lifecycle,
            volume=volume,
        )

        core.start()
        core.close()

        volume.refresh.assert_called_once_with()
        map_camera.start.assert_called_once_with()
        ingress.start.assert_called_once_with()
        trip_runtime.start.assert_called_once_with()
        trip_runtime.close.assert_called_once_with()
        ingress.close.assert_called_once_with()
        trip_publisher.close.assert_called_once_with()
        map_camera.close.assert_called_once_with()
        map_runtime.stop.assert_called_once_with()

    @patch("apps.orcUi.composition.core.ZeroMqSubscriber")
    @patch("apps.orcUi.composition.core.ZeroMqPublisher")
    @patch("apps.orcUi.composition.core.TripRuntime")
    @patch("apps.orcUi.composition.core.PipewireAudioController")
    @patch("apps.orcUi.composition.core.SystemVolumeHandler")
    @patch("apps.orcUi.composition.core.SystemLifecycleController")
    @patch("apps.orcUi.composition.core.StateIngressRuntime")
    @patch("apps.orcUi.composition.core.OrcUiApp")
    @patch("apps.orcUi.composition.core.MapCameraRuntime")
    @patch("apps.orcUi.composition.core.MapRuntime")
    def test_factory_injects_shell_runtime_dependencies_and_ui_state_sinks(
        self,
        map_runtime_type: Mock,
        map_camera_type: Mock,
        app_type: Mock,
        ingress_type: Mock,
        lifecycle_type: Mock,
        volume_type: Mock,
        audio_type: Mock,
        trip_runtime_type: Mock,
        publisher_type: Mock,
        subscriber_type: Mock,
    ) -> None:
        map_runtime = map_runtime_type.return_value
        map_camera = map_camera_type.return_value
        lifecycle = lifecycle_type.return_value
        audio = audio_type.return_value
        volume = volume_type.return_value
        app = app_type.return_value

        core = create_core_composition()

        map_camera_type.assert_called_once_with(
            zoom_level=16.5,
            pitch_rad=math.radians(45.0),
            follow_enabled=True,
        )
        app_type.assert_called_once()
        app_kwargs = app_type.call_args.kwargs
        self.assertIs(app_kwargs["map_runtime"], map_runtime)
        self.assertIs(app_kwargs["map_request_handler"], map_camera.request_handler)
        self.assertIs(app_kwargs["lifecycle_handler"], lifecycle)
        self.assertTrue(callable(app_kwargs["telemetry_profile_request"]))
        self.assertIsNotNone(app_kwargs["vehicle_configuration"])
        self.assertTrue(callable(app_kwargs["save_vehicle_configuration"]))
        volume_type.assert_called_once_with(
            audio_controller=audio,
            volume_ui=app,
            set_status=app.set_screen_status,
        )
        app.set_volume_request_handler.assert_called_once_with(volume)
        ingress_type.assert_called_once()
        ingress_kwargs = ingress_type.call_args.kwargs
        self.assertIs(ingress_kwargs["schedule_ui"], app.schedule_ui_callback)
        self.assertIs(ingress_kwargs["apply_vehicle_state"], app.apply_vehicle_state)
        self.assertIs(ingress_kwargs["apply_engine_analysis"], app.apply_engine_analysis)
        self.assertIs(ingress_kwargs["apply_trip_state"], app.apply_trip_state)
        self.assertIs(ingress_kwargs["apply_position_state"], app.apply_position_state)
        self.assertIs(ingress_kwargs["apply_attitude_state"], app.apply_attitude_state)
        self.assertIsNotNone(ingress_kwargs["vehicle_configuration"])
        app.set_vehicle_configuration_observer.assert_called_once_with(
            ingress_type.return_value.set_vehicle_configuration
        )
        self.assertIs(core.app, app)
        self.assertIs(core.map_runtime, map_runtime)
        self.assertIs(core.map_camera, map_camera)
        self.assertIs(core.state_ingress, ingress_type.return_value)
        self.assertIs(core.trip_runtime, trip_runtime_type.return_value)
        self.assertIs(core.trip_publisher, publisher_type.return_value)
        self.assertIs(core.lifecycle, lifecycle)
        self.assertIs(core.volume, volume)


if __name__ == "__main__":
    unittest.main()
