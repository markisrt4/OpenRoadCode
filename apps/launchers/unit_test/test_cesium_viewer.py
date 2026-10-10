"""Standalone viewer state, transport isolation, and resource ownership."""

from pathlib import Path
import urllib.error
import urllib.request
import json
import math
import re
from unittest.mock import Mock, patch

import pytest

from apps.launchers.cesium_viewer_server import CesiumViewerServer
from apps.launchers.component_test.cesium_viewer_cli import run
from ui.navigation import GeoPoint
from ui.navigation.cesium_viewer_state import CesiumViewerState


@pytest.fixture
def state():
    return CesiumViewerState(GeoPoint(math.radians(42.3314), math.radians(-83.0458)))


@pytest.fixture
def server(tmp_path, state):
    sdk = tmp_path / "sdk"
    (sdk / "Widgets").mkdir(parents=True)
    (sdk / "Assets").mkdir()
    (sdk / "Workers").mkdir()
    (sdk / "Cesium.js").write_text("sdk")
    (sdk / "Widgets/widgets.css").write_text("css")
    server = CesiumViewerServer(sdk, state)
    server.start()
    yield server
    server.close()


@pytest.mark.parametrize("latitude,longitude", [(math.nan,0), (2,0), (0,4)])
def test_invalid_destination_cannot_reach_browser(latitude, longitude):
    with pytest.raises(ValueError):
        CesiumViewerState(GeoPoint(latitude,longitude))


def test_local_state_and_sdk_are_served_without_dataset_credentials(server, state):
    with urllib.request.urlopen(server.url + "config.json") as response:
        document = json.load(response)
    assert document["latitude_rad"] == state.destination.latitude_rad
    assert document["tilt_rad"] == math.pi/4
    assert "close_token" in document
    with urllib.request.urlopen(server.url + "sdk/Cesium.js") as response:
        assert response.read() == b"sdk"


def test_server_does_not_expose_files_outside_asset_mount(server):
    with pytest.raises(urllib.error.HTTPError) as failure:
        urllib.request.urlopen(server.url + "sdk/%2e%2e/secret.txt")
    assert failure.value.code == 404


def test_foreign_host_cannot_read_close_token(server):
    request = urllib.request.Request(server.url + "config.json", headers={"Host":"foreign.example"})
    with pytest.raises(urllib.error.HTTPError) as failure:
        urllib.request.urlopen(request)
    assert failure.value.code == 403


def test_only_authorized_close_requests_stop_this_viewer(server):
    request = urllib.request.Request(server.url + "close", method="POST")
    with pytest.raises(urllib.error.HTTPError) as failure:
        urllib.request.urlopen(request)
    assert failure.value.code == 403
    assert not server.close_requested.is_set()
    with urllib.request.urlopen(server.url + "config.json") as response:
        token = json.load(response)["close_token"]
    request = urllib.request.Request(server.url + "close", method="POST", headers={"X-ORC-Token":token})
    with urllib.request.urlopen(request) as response:
        assert response.status == 200
    assert server.close_requested.wait(1)


@pytest.mark.parametrize("fails", [False, True])
def test_launcher_owns_only_isolated_browser_and_cleans_up_on_start_failure(state, fails):
    server, browser = Mock(), Mock()
    server.close_requested.wait.return_value = True
    if fails:
        browser.launch.side_effect = RuntimeError("browser failed")
    calls = Mock()
    calls.attach_mock(browser.stop, "browser_stop")
    calls.attach_mock(server.close, "server_close")
    with (
        patch("apps.launchers.component_test.cesium_viewer_cli.CesiumViewerServer", return_value=server),
        patch("apps.launchers.component_test.cesium_viewer_cli.BrowserKioskLauncher", return_value=browser) as create,
        patch("apps.launchers.component_test.cesium_viewer_cli.logging_file_path", return_value=Path("unused.log")),
    ):
        if fails:
            with pytest.raises(RuntimeError, match="browser failed"):
                run(state, Path("sdk"), ":1")
        else:
            assert run(state, Path("sdk"), ":1") == 0
    arguments = create.call_args.kwargs
    assert re.fullmatch(arguments["process_pattern"], arguments["profile_path"])
    assert not arguments["kiosk"]
    assert not Path(arguments["profile_path"]).exists()
    assert [call[0] for call in calls.mock_calls] == ["browser_stop", "server_close"]


def test_layer_defaults_and_visibility_contract(state):
    from dataclasses import replace
    assert state.document()['buildings_visible'] is True
    assert state.document()['references_visible'] is False
    assert state.distance_m == 1500
    changed = replace(state, buildings_visible=False, references_visible=True)
    assert changed.document()['buildings_visible'] is False
    assert changed.document()['references_visible'] is True
    with pytest.raises(ValueError, match='boolean'):
        replace(state, references_visible='yes')


def test_terrain_visibility_is_explicit_boolean_snapshot_state(state):
    from dataclasses import replace
    assert state.document()['terrain_visible'] is True
    assert replace(state, terrain_visible=False).document()['terrain_visible'] is False
    with pytest.raises(ValueError, match='visibility'):
        replace(state, terrain_visible='false')


def test_pitch_control_contract_uses_finite_si_angles(state):
    from dataclasses import replace
    import math
    assert state.document()['pitch_step_rad'] == math.pi/18
    assert 0 < state.document()['maximum_tilt_rad'] < math.pi/2
    for step, limit in ((0, 1), (1, math.pi/2), (float('nan'), 1)):
        with pytest.raises(ValueError, match='pitch'):
            replace(state, pitch_step_rad=step, maximum_tilt_rad=limit)
