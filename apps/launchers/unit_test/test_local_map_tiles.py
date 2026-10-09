import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

import pytest

from apps.launchers.local_map_tiles_pack import LocalMapTilesPack
from development.maps import download_detroit_map_tiles as downloader


def fixture_image(destination, *, bounds):
    destination.mkdir()
    image = b'\xff\xd8fixture'
    (destination/'imagery.jpg').write_bytes(image)
    (destination/'manifest.json').write_text(json.dumps({'schema':1,'image':'imagery.jpg',
        'bounds_deg':bounds,'title':'Test NAIP','attribution':'Test USGS',
        'sha256':hashlib.sha256(image).hexdigest()}))


def install(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader,'download_imagery',fixture_image)
    monkeypatch.setattr(downloader,'request_tile',lambda bounds:b'{"elements":[]}')
    destination = tmp_path/'pack'
    downloader.download(destination)
    return destination


def test_pack_install_keeps_empty_tiles_sources_and_bounds(tmp_path,monkeypatch):
    destination = install(tmp_path,monkeypatch)
    pack = LocalMapTilesPack.load(destination)
    assert len(pack.state.tiles) == 8
    assert all(t.buildings_count == 0 for t in pack.state.tiles)
    assert (destination/'r0-c0/source-osm.json').exists()
    assert pack.state.document()['tiles'][0]['imagery_url'] == '/data/tiles/r0-c0/imagery.jpg'
    (destination/'r0-c0/imagery.jpg').write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'):
        LocalMapTilesPack.load(destination)


def test_tile_identifier_cannot_escape_pack(tmp_path,monkeypatch):
    destination = install(tmp_path,monkeypatch)
    manifest = json.loads((destination/'manifest.json').read_text())
    manifest['tiles'][0]['id'] = '../escape'
    (destination/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='identifier'):
        LocalMapTilesPack.load(destination)


def test_only_manifested_assets_are_served(tmp_path,monkeypatch,server):
    # Shared server fixture keeps the test independent of the native browser.
    server._tiles = LocalMapTilesPack.load(install(tmp_path,monkeypatch))
    with urllib.request.urlopen(server.url+'config.json') as response:
        data = json.load(response)
    assert len(data['map_tiles']['tiles']) == 8
    with urllib.request.urlopen(server.url+'data/tiles/r0-c0/imagery.jpg') as response:
        assert response.read() == b'\xff\xd8fixture'
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(server.url+'data/tiles/r0-c0/source-osm.json')
    assert error.value.code == 404


def test_camera_tile_lifecycle_js():
    node = shutil.which('node')
    if not node:
        pytest.skip('Optional Node JS check')
    path = Path(__file__).resolve().parents[3]/'frontends/web/cesium/unit_test/test_local_map_tiles.js'
    result = subprocess.run([node,'--test',str(path)],capture_output=True,text=True,timeout=20)
    assert result.returncode == 0, result.stdout+result.stderr


from apps.launchers.unit_test.test_cesium_viewer import server, state  # noqa: E402,F401


def test_interrupted_pack_resumes_completed_requests(tmp_path,monkeypatch):
    image_calls, osm_calls = [], []

    def image(destination, *, bounds):
        if destination.exists():
            return
        image_calls.append(bounds)
        fixture_image(destination,bounds=bounds)

    def osm(bounds):
        osm_calls.append(bounds)
        if len(osm_calls) == 2:
            raise TimeoutError('service busy')
        return b'{"elements":[]}'

    monkeypatch.setattr(downloader,'download_imagery',image)
    monkeypatch.setattr(downloader,'request_tile',osm)
    destination = tmp_path/'pack'
    with pytest.raises(TimeoutError):
        downloader.download(destination)
    assert not destination.exists()
    assert (tmp_path/'pack.download/r0-c0/source-osm.json').exists()
    monkeypatch.setattr(downloader,'request_tile',lambda bounds:osm_calls.append(bounds) or b'{"elements":[]}')
    downloader.download(destination)
    assert len(image_calls) == 8
    assert len(osm_calls) == 9  # Eight successes plus the failed request; tile zero was cached.
    assert len(LocalMapTilesPack.load(destination).state.tiles) == 8
