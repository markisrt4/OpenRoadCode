"""Suburban outlines, terrain selection and source-independent installation checks."""

import json
import math
from unittest.mock import Mock

import pytest

from apps.launchers import local_map_tiles_pack, local_terrain_pack
from development.maps import download_detroit_map_tiles as builder
from tools.map_builder.builder.map_3d import PRESETS
from ui.navigation import GeoPoint


@pytest.mark.parametrize('region',['rochester','southfield'])
def test_suburban_buildings_only_pack_is_selected_at_its_location(tmp_path,monkeypatch,region):
    title,bounds=PRESETS[region]
    destination=tmp_path/(region+'-buildings-v1')
    imagery=Mock(side_effect=AssertionError('imagery requested'))
    monkeypatch.setattr(builder,'download_imagery',imagery)
    def source(bounds):
        west,south,east,north=bounds
        lon,lat=(west+east)/2,(south+north)/2
        return json.dumps({'elements':[{'type':'way','id':1,'tags':{'building':'yes','building:levels':'2'},
            'geometry':[{'lon':lon,'lat':lat},{'lon':lon+.00001,'lat':lat},
                        {'lon':lon+.00001,'lat':lat+.00001},{'lon':lon,'lat':lat}]}]}).encode()
    monkeypatch.setattr(builder,'request_tile',source)
    builder.download(destination,bounds=bounds,title=title,imagery=False)
    pack=local_map_tiles_pack.LocalMapTilesPack.load(destination)
    assert sum(tile.buildings_count for tile in pack.state.tiles) == 8
    assert all(not tile.imagery_available for tile in pack.state.tiles)
    imagery.assert_not_called()
    monkeypatch.setattr(local_map_tiles_pack,'navigation_data_root',lambda:tmp_path/'shared')
    monkeypatch.setattr(local_map_tiles_pack,'openroadcode_data_dir',lambda *parts:tmp_path/parts[-1])
    point=GeoPoint(math.radians((bounds[1]+bounds[3])/2),math.radians((bounds[0]+bounds[2])/2))
    assert local_map_tiles_pack.preferred_tiles_directory(point) == destination
    terrain=tmp_path/(region+'-terrain-v1')
    terrain.mkdir()
    (terrain/'manifest.json').write_text(json.dumps({'bounds_deg':bounds}))
    monkeypatch.setattr(local_terrain_pack,'navigation_data_root',lambda:tmp_path/'shared')
    monkeypatch.setattr(local_terrain_pack,'openroadcode_data_dir',lambda *parts:tmp_path/parts[-1])
    assert local_terrain_pack.preferred_terrain_directory(point) == terrain
