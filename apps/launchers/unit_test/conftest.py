"""Shared isolated Cesium HTTP server fixtures."""

import math

import pytest

from apps.launchers.cesium_viewer_server import CesiumViewerServer
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
