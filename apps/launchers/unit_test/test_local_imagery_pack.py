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


def test_transparent_overview_is_served_as_png(server, pack):
    (pack/'imagery.jpg').rename(pack/'imagery.png')
    manifest = json.loads((pack/'manifest.json').read_text())
    manifest['image'] = 'imagery.png'
    (pack/'manifest.json').write_text(json.dumps(manifest))
    server._imagery = LocalImageryPack.load(pack)
    with urllib.request.urlopen(server.url+'data/imagery.jpg') as response:
        assert response.headers['Content-Type'] == 'image/png'


def test_installed_overview_and_detail_are_ordered_broad_to_fine(tmp_path,monkeypatch):
    from apps.launchers import local_imagery_pack as packs
    from apps.launchers.unit_test.test_region_install import write_pack
    overview=tmp_path/'overview'
    detail=tmp_path/'detail'
    write_pack(overview,title='Metro',bounds=(-84,42,-82,44))
    write_pack(detail,title='Detail',bounds=(-83.1,42.3,-83,42.4))
    monkeypatch.setattr(packs,'installed_imagery_directories',lambda:(detail,overview))
    stack=packs.load_imagery_stack()
    assert [pack.state.title for pack in stack] == ['Metro','Detail']


def test_server_mounts_checked_stack_layers_without_exposing_paths(server,pack):
    from ui.navigation.local_imagery_state import LocalImageryStackState
    loaded=LocalImageryPack.load(pack)
    server._imagery_layers=(loaded,loaded)
    server._imagery_stack=LocalImageryStackState((loaded.state,loaded.state))
    with urllib.request.urlopen(server.url+'config.json') as response:
        layers=json.load(response)['imagery_layers']
    assert [layer['url'] for layer in layers] == ['/data/imagery/0','/data/imagery/1']
    with urllib.request.urlopen(server.url+'data/imagery/1') as response:
        assert response.read() == loaded.image.read_bytes()
    with pytest.raises(HTTPError):
        urllib.request.urlopen(server.url+'data/imagery/2')


def test_server_exposes_only_bounded_offline_road_tiles(server):
    from unittest.mock import Mock
    from ui.navigation.road_overlay_state import RoadOverlayState
    server._roads=Mock(max_zoom=14)
    server._roads.tile.return_value=RoadOverlayState()
    with urllib.request.urlopen(server.url+'data/roads/12/1234/1500') as response:
        assert json.load(response)['attribution'].startswith('© OpenStreetMap')
    server._roads.tile.assert_called_once_with(12,1234,1500)
    with pytest.raises(HTTPError):
        urllib.request.urlopen(server.url+'data/roads/not-a-tile')
