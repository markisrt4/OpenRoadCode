"""Regional ownership, safe batch installation, and cross-region serving metadata."""
import io
import json
import math
from pathlib import Path
from unittest.mock import Mock

import pytest

from development.maps.terrain_regions import MICHIGAN_SHARDS
from tools.map_builder.builder import map_3d
from tools.map_builder.builder.building_artifact import package, limits
from apps.launchers import local_map_tiles_pack as runtime
from apps.launchers import local_building_regions as regions
from development.maps import install_buildings as installer


def fixture_pack(root,key):
    title,bounds=map_3d.PRESETS[key]
    w,s,e,n=bounds;x,y=(w+e)/2,(s+n)/2
    ring=[[math.radians(lon),math.radians(lat)] for lon,lat in [(x,y),(x+.001,y),(x,y+.001),(x,y)]]
    root.mkdir(parents=True)
    tile=root/'r0-c0';tile.mkdir()
    (tile/'buildings.json').write_text(json.dumps(dict(attribution=map_3d.CREDIT,buildings=[
        dict(ring_rad=ring,height_m=9,height_source='placeholder')])))
    manifest=dict(schema=3,coverage=key,title=title,attribution=map_3d.CREDIT,bounds_deg=bounds,layers=['buildings'],
                  tiles=[dict(id='r0-c0',title=title,attribution=map_3d.CREDIT,bounds_deg=bounds,
                              buildings_count=1,sha256={'buildings.json':map_3d.digest(tile/'buildings.json')})])
    (root/'manifest.json').write_text(json.dumps(manifest))
    return root


def patch_device(monkeypatch,tmp_path):
    def data(*parts):return tmp_path.joinpath(*parts)
    for module in (installer,regions,runtime):
        monkeypatch.setattr(module,'openroadcode_data_dir',data)
    monkeypatch.setattr(regions,'navigation_data_root',lambda:tmp_path/'shared')
    monkeypatch.setattr(runtime,'navigation_data_root',lambda:tmp_path/'shared')


def test_all_eight_packs_install_and_mount_without_duplicate_metro_or_tile_ids(tmp_path,monkeypatch):
    patch_device(monkeypatch,tmp_path/'device')
    downloads=tmp_path/'downloads'
    for key in MICHIGAN_SHARDS:
        pack=fixture_pack(tmp_path/'source'/key,key)
        package(pack,downloads/key/(key+'-buildings.zip'),key)
    installer.install_michigan(downloads)
    metro=fixture_pack(tmp_path/'device/map-packs/metro-detroit-buildings-active','metro-detroit')
    pack=runtime.load_viewer_tiles(runtime.preferred_tiles_directory())
    assert len(pack.state.tiles)==8 and len(pack.files)==8
    assert len({tile.tile_id for tile in pack.state.tiles})==8
    assert all(not path.is_relative_to(metro) for mounted in pack.files.values() for path in mounted.values())
    assert all(tile.document()['buildings_url'].endswith(tile.tile_id+'/buildings.json') for tile in pack.state.tiles)
    assert pack.state.coverage.west_rad==math.radians(-90.5)
    assert pack.state.coverage.east_rad==math.radians(-82.1)
    assert pack.state.coverage.north_rad==math.radians(48.3)


def test_partial_michigan_keeps_existing_metro_when_southeast_is_not_installed(tmp_path,monkeypatch):
    patch_device(monkeypatch,tmp_path)
    fixture_pack(tmp_path/'map-packs/mi-upper-west-buildings-active','mi-upper-west')
    fixture_pack(tmp_path/'map-packs/metro-detroit-buildings-active','metro-detroit')
    pack=runtime.load_viewer_tiles(runtime.preferred_tiles_directory())
    assert len(pack.state.tiles)==2


def test_missing_archive_preflight_does_not_install_partial_batch(tmp_path,monkeypatch):
    calls=Mock();monkeypatch.setattr(installer,'install',calls)
    with pytest.raises(ValueError,match='Expected one'):
        installer.install_michigan(tmp_path)
    calls.assert_not_called()


def test_wrong_region_archive_cannot_replace_active_pack(tmp_path):
    key='mi-upper-west';pack=fixture_pack(tmp_path/'source',key)
    archive=tmp_path/(key+'-buildings.zip');package(pack,archive,key)
    active=tmp_path/'active'
    with pytest.raises(ValueError,match='coverage'):
        installer.install(archive,coverage='mi-upper-east',destination=active)
    assert not active.exists()
    assert limits('metro-detroit')==(128*1024**2,512*1024**2)
    assert limits(key)==(256*1024**2,1024**3)


def test_components_crossing_region_edges_are_retained_once(tmp_path,monkeypatch):
    source=tmp_path/'maps/source/source.osm.pbf';source.parent.mkdir(parents=True);source.write_bytes(b'fixture')
    def feature(identity,west,east):
        return dict(id=identity,properties={'building':'yes'},geometry=dict(type='Polygon',coordinates=[
            [[west,42.4],[east,42.4],[east,42.401],[west,42.401],[west,42.4]]]))
    # Both cross the -84.3 regional boundary but their centroids lie on different sides.
    fixtures=[feature('w1',-84.302,-84.299),feature('w2',-84.301,-84.298)]
    monkeypatch.setattr(map_3d.subprocess,'run',Mock(return_value=Mock(stdout='')))
    def process(*args,**kwargs):
        p=Mock(stdout=io.StringIO('\n'.join(json.dumps(f) for f in fixtures)));p.wait.return_value=0
        return p
    monkeypatch.setattr(map_3d.subprocess,'Popen',process)
    results=[]
    for key in ('mi-lower-southwest','mi-lower-southeast'):
        pack=map_3d.build_pack(tmp_path,key)
        results.append(map_3d.validate_pack(pack)['buildings'])
    assert results==[1,1]


def test_overlapping_upper_and_lower_envelopes_have_deterministic_single_owner():
    point=[math.radians(-85.5),math.radians(45.8)]
    building={'ring_rad':[point,point,point,point]}
    assert map_3d.regional_owner(building)=='mi-lower-northwest'


def test_southern_border_strip_is_included_without_changing_terrain_coverage():
    point=[math.radians(-83.5),math.radians(41.697)]
    assert map_3d.regional_owner({'ring_rad':[point]*4})=='mi-lower-southeast'
    assert MICHIGAN_SHARDS['mi-lower-southeast'][1][1]==41.7
    assert map_3d.PRESETS['mi-lower-southeast'][1][1]<41.696089
