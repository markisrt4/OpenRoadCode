import hashlib
import json
import math

import pytest

from apps.launchers.local_building_pack import load_buildings
from development.maps.download_detroit_buildings import prepare, height
from ui.navigation.local_building_state import LocalBuilding


def test_height_provenance_and_unsupported_units():
    assert height({'height':'100 m'}) == (100, 'osm-height')
    assert height({'building:levels':'8'}) == (24, 'levels-estimate')
    assert height({'height':'100 ft'}) == (9, 'placeholder')
    assert height({'height':'nan', 'building:levels':'-2'}) == (9, 'placeholder')


def test_closed_bounded_ways_only_and_server_errors():
    geometry = [{'lon':-83.05,'lat':42.33}, {'lon':-83.049,'lat':42.33},
                {'lon':-83.049,'lat':42.331}, {'lon':-83.05,'lat':42.33}]
    way = {'type':'way','tags':{'building':'yes'},'geometry':geometry}
    state, skipped = prepare({'elements':[way, {**way,'geometry':geometry[:-1]}]})
    assert skipped == 1
    assert state.buildings[0].ring[0] == (math.radians(-83.05),math.radians(42.33))
    with pytest.raises(RuntimeError):
        prepare({'remark':'Query timed out', 'elements':[way]})


def test_pack_integrity_and_invalid_geometry(tmp_path):
    building = LocalBuilding(((0,0),(0.01,0),(0,0.01),(0,0)),9,'placeholder')
    data = json.dumps({'buildings':[building.document()], 'attribution':'OSM contributors'}).encode()
    (tmp_path/'buildings.json').write_bytes(data)
    (tmp_path/'manifest.json').write_text(json.dumps({'schema':1,'sha256':hashlib.sha256(data).hexdigest()}))
    assert load_buildings(tmp_path).buildings == (building,)
    (tmp_path/'buildings.json').write_bytes(data+b' ')
    with pytest.raises(ValueError, match='checksum'):
        load_buildings(tmp_path)
    with pytest.raises(ValueError):
        LocalBuilding(((0,0),(1,0),(0,1),(1,1)),9,'placeholder')


def test_download_retains_source_and_installs_validated_pack(tmp_path, monkeypatch):
    from io import BytesIO
    from development.maps import download_detroit_buildings as downloader
    reply = {'elements':[{'type':'way', 'tags':{'building':'yes','height':'50'},
        'geometry':[{'lon':-83.05,'lat':42.33}, {'lon':-83.049,'lat':42.33},
                    {'lon':-83.049,'lat':42.331}, {'lon':-83.05,'lat':42.33}]}]}
    monkeypatch.setattr(downloader.urllib.request, 'urlopen',
                        lambda *args, **kwargs: BytesIO(json.dumps(reply).encode()))
    destination = tmp_path/'pack'
    downloader.download(destination)
    assert load_buildings(destination).buildings[0].height_m == 50
    assert json.loads((destination/'source-osm.json').read_text()) == reply
    assert json.loads((destination/'manifest.json').read_text())['license'] == 'ODbL-1.0'
