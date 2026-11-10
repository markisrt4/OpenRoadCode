# SPDX-License-Identifier: MIT
"""Inject failures at core acquisition boundaries without opening transports."""

from contextlib import ExitStack
from unittest.mock import Mock, patch

import pytest

from apps.orcUi.composition.core import create_core_composition
from apps.orcUi.composition.application import OrcUiComposition
from apps.orcUi.application_runtime import OrcUiApplicationRuntime


@pytest.mark.parametrize("failed", ["MapCameraRuntime", "OrcUiApp", "StateIngressRuntime", "TripRuntime"])
def test_core_factory_rolls_back_every_acquired_owner(failed):
    names = (
        "MapRuntime", "MapCameraRuntime", "NavigationCommandClient",
        "NavigationRouteRequestHandler", "SystemLifecycleController", "OrcUiApp",
        "ShellConnectivityController", "SystemVolumeHandler", "PipewireAudioController",
        "StateIngressRuntime", "ZeroMqPublisher", "ZeroMqSubscriber", "TripRuntime",
    )
    startup = RuntimeError("startup failure")
    with ExitStack() as stack:
        factories = {name: stack.enter_context(patch(f"apps.orcUi.composition.core.{name}"))
                     for name in names}
        publishers = []

        def publisher(*args):
            resource = Mock()
            publishers.append(resource)
            return resource

        factories["ZeroMqPublisher"].side_effect = publisher
        factories[failed].side_effect = startup
        # A rollback failure must neither mask startup nor skip later resources.
        factories["MapRuntime"].return_value.stop.side_effect = ValueError("stop failure")
        with pytest.raises(RuntimeError) as caught:
            create_core_composition()
        assert caught.value is startup
        assert "stop failure" in startup.__notes__[0]
        for name, method in (
            ("MapRuntime", "stop"), ("MapCameraRuntime", "close"),
            ("NavigationRouteRequestHandler", "close"), ("OrcUiApp", "shutdown"),
            ("ShellConnectivityController", "close"), ("StateIngressRuntime", "close"),
            ("ZeroMqSubscriber", "close"),
        ):
            factory = factories[name]
            if factory.called and name != failed:
                getattr(factory.return_value, method).assert_called_once()
        for resource in publishers:
            resource.close.assert_called_once()


def test_application_start_failure_preserves_error_and_closes_once():
    resources = {name: Mock() for name in ("core", "runtime", "radio", "games", "media", "weather")}
    composition = OrcUiComposition(**resources)
    startup = RuntimeError("ingress startup")
    resources["core"].start.side_effect = startup
    resources["games"].shutdown.side_effect = ValueError("games cleanup")
    with pytest.raises(RuntimeError) as caught:
        composition.run()
    assert caught.value is startup
    assert "games cleanup" in startup.__notes__[0]
    composition.close()
    resources["core"].app.shutdown.assert_called_once()
    resources["games"].shutdown.assert_called_once()
    for name in ("media", "weather", "core", "runtime"):
        resources[name].close.assert_called_once()
    resources["core"].lifecycle.execute_requested_action.assert_not_called()


def test_runtime_closes_media_and_apps_when_streaming_close_fails():
    manager, radio, streaming, media = (Mock() for _ in range(4))
    runtime = OrcUiApplicationRuntime(manager, radio, streaming, media)
    streaming.close.side_effect = RuntimeError("streaming")
    with pytest.raises(RuntimeError, match="streaming"):
        runtime.close()
    runtime.close()
    streaming.close.assert_called_once()
    media.close.assert_called_once()
    manager.stop_all.assert_called_once()


@pytest.mark.parametrize("earth_enabled", [False, True])
def test_runtime_preserves_earth_policy_and_terminal_cleanup(earth_enabled):
    from apps.orcUi.application_runtime import create_orc_ui_application_runtime

    names = ("ApplicationsConfigParser", "AppRuntimeManager", "ManagedSDRPPLauncher",
             "BrowserApplicationFactory", "GoogleEarthLauncher", "StreamingRadioController",
             "MpvStreamingAudioPlayer", "MediaApplicationService", "create_spotify_controller")
    with ExitStack() as stack:
        factories = {name: stack.enter_context(patch(f"apps.orcUi.application_runtime.{name}"))
                     for name in names}
        config = factories["ApplicationsConfigParser"].return_value.load.return_value
        config.app.side_effect = lambda key: Mock(enabled=earth_enabled, fullscreen=False)
        runtime = create_orc_ui_application_runtime()
        manager = factories["AppRuntimeManager"].return_value
        earth_factory = factories["GoogleEarthLauncher"]
        if earth_enabled:
            assert runtime.earth is earth_factory.return_value
            manager.register.assert_any_call("google_earth", runtime.earth)
        else:
            assert runtime.earth is None
            earth_factory.assert_not_called()
        runtime.close()
        runtime.close()
        manager.stop_all.assert_called_once_with()


def test_earth_construction_failure_rolls_back_application_manager():
    from apps.orcUi.application_runtime import create_orc_ui_application_runtime

    with patch("apps.orcUi.application_runtime.ApplicationsConfigParser"), patch(
        "apps.orcUi.application_runtime.AppRuntimeManager") as manager, patch(
        "apps.orcUi.application_runtime.ManagedSDRPPLauncher"), patch(
        "apps.orcUi.application_runtime.BrowserApplicationFactory"), patch(
        "apps.orcUi.application_runtime.GoogleEarthLauncher", side_effect=RuntimeError("Earth startup")):
        with pytest.raises(RuntimeError, match="Earth startup"):
            create_orc_ui_application_runtime()
    manager.return_value.stop_all.assert_called_once_with()
