"""Imagery checksum, coverage, attribution, and mounting remain separate from UI."""

import hashlib
import json
import math
from urllib.error import HTTPError
import urllib.request

import pytest

from apps.launchers.local_imagery_pack import LocalImageryPack
from apps.launchers.cesium_viewer_server import CesiumViewerServer
from ui.navigation import GeoPoint
from ui.navigation.cesium_viewer_state import CesiumViewerState
from ui.navigation.local_imagery_state import LocalImageryState
from apps.launchers.unit_test.test_cesium_viewer import server, state  # shared isolated HTTP fixture


@pytest.fixture
def pack(tmp_path):
    root = tmp_path / "pack"
    root.mkdir()
    image = b"\xff\xd8fixture"
    (root / "imagery.jpg").write_bytes(image)
    manifest = {"schema":1,"image":"imagery.jpg","sha256":hashlib.sha256(image).hexdigest(),
                "title":"Detroit fixture","attribution":"USGS fixture", "bounds_deg":[-83.065,42.315,-83.025,42.345]}
    (root / "manifest.json").write_text(json.dumps(manifest))
    return root


def test_pack_normalizes_coverage_and_keeps_paths_out_of_state(pack):
    loaded = LocalImageryPack.load(pack)
    assert loaded.state.west_rad == math.radians(-83.065)
    assert "image" not in loaded.state.document()
    assert loaded.state.attribution == "USGS fixture"


def test_modified_image_is_rejected_before_browser_launch(pack):
    (pack / "imagery.jpg").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        LocalImageryPack.load(pack)


def test_pack_cannot_mount_an_external_file(pack):
    document = json.loads((pack / "manifest.json").read_text())
    external = pack.parent / "outside.jpg"
    external.write_bytes(b"outside")
    document["image"] = "../outside.jpg"
    (pack / "manifest.json").write_text(json.dumps(document))
    with pytest.raises(ValueError, match="inside"):
        LocalImageryPack.load(pack)


def test_coverage_and_attribution_are_required():
    with pytest.raises(ValueError):
        LocalImageryState("title","",-.1,.1,.1,.2)
    with pytest.raises(ValueError):
        LocalImageryState("title","credit",.1,.1,-.1,.2)


def test_server_mounts_only_selected_image_and_exposes_coverage(server, pack):
    server._imagery = LocalImageryPack.load(pack)
    with urllib.request.urlopen(server.url+"config.json") as response:
        document = json.load(response)
    assert document["imagery"]["url"] == "/data/imagery.jpg"
    assert document["imagery"]["attribution"] == "USGS fixture"
    with urllib.request.urlopen(server.url+"data/imagery.jpg") as response:
        assert response.read() == b"\xff\xd8fixture"
    with pytest.raises(HTTPError) as error:
        urllib.request.urlopen(server.url+"data/manifest.json")
    assert error.value.code == 404
