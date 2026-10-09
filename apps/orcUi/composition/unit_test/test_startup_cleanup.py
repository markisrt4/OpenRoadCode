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
