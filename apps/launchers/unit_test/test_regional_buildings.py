"""OSM source extraction through checked archive activation and runtime selection."""

import math
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

from tools.map_builder.builder.map_3d import PRESETS, build_pack, validate_pack
from tools.map_builder.builder.building_artifact import package
from development.maps.install_buildings import install
from apps.launchers import local_map_tiles_pack as runtime
from ui.navigation import GeoPoint


@pytest.fixture
def artifact(tmp_path):
    if not shutil.which('osmium'):
        pytest.skip('osmium is required only on map build host')
    root=tmp_path/'dataset'
    source=root/'maps/source/michigan.osm.pbf'
    source.parent.mkdir(parents=True)
    osm=tmp_path/'fixture.osm'
    osm.write_text('''<osm version="0.6" generator="ORC test">
<node id="1" version="1" lat="42.33" lon="-83.05"/>
<node id="2" version="1" lat="42.33" lon="-83.049"/>
<node id="3" version="1" lat="42.331" lon="-83.049"/>
<node id="4" version="1" lat="42.331" lon="-83.05"/>
<way id="10" version="1"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
<tag k="building" v="yes"/><tag k="building:levels" v="5"/></way></osm>''')
    subprocess.run(['osmium','cat',str(osm),'-o',str(source)],check=True)
    pack=build_pack(root,'metro-detroit')
    archive=tmp_path/'metro-detroit-buildings.zip'
    descriptor=package(pack,archive,'metro-detroit')
    return pack,archive,descriptor


def test_osm_pbf_becomes_bounded_installable_regional_buildings(artifact,tmp_path,monkeypatch):
    pack,archive,descriptor=artifact
    assert descriptor['buildings']==1 and descriptor['height_counts']['levels-estimate']==1
    assert descriptor['tiles']==1024
    assert validate_pack(pack)['buildings']==1
    active=tmp_path/'device/metro-detroit-buildings-active'
    install(archive,destination=active)
    assert active.is_symlink()
    loaded=runtime.LocalMapTilesPack.load(active)
    assert len(loaded.state.tiles)==1024
    assert all(not tile.imagery_available for tile in loaded.state.tiles)
    assert sum(tile.buildings_count for tile in loaded.state.tiles)==1
    monkeypatch.setattr(runtime,'openroadcode_data_dir',lambda *args:active)
    monkeypatch.setattr(runtime,'navigation_data_root',lambda:tmp_path/'nav')
    assert runtime.preferred_tiles_directory(GeoPoint(math.radians(42.33),math.radians(-83.05)))==active
    previous=active.resolve()
    # A changed archive cannot replace a working revision.
    with archive.open('ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='size'):
        install(archive,destination=active)
    assert active.resolve()==previous


def test_building_archive_rejects_path_traversal_before_activation(tmp_path):
    from development.maps.prebuilt_imagery import unpack
    archive=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as zipped:zipped.writestr('../outside','bad')
    with pytest.raises(ValueError,match='Unsafe'):
        unpack(archive,tmp_path/'revision',PRESETS['metro-detroit'][1],loader=validate_pack,
               max_unpacked_bytes=512*1024*1024)
    assert not (tmp_path/'outside').exists()


def test_wrong_kind_cannot_activate_buildings(tmp_path,monkeypatch):
    from development.maps import install_buildings as installer
    monkeypatch.setattr(installer,'read_local_archive',lambda *args:({'kind':'terrain'},Path('fake.zip')))
    with pytest.raises(ValueError,match='not a buildings'):
        installer.install(Path('fake.zip'),destination=tmp_path/'active')
    assert not (tmp_path/'active').exists()


@pytest.mark.parametrize('region_id',['michigan','north-america/us/michigan'])
def test_source_selection_uses_official_url_instead_of_catalog_id_shape(region_id):
    from tools.map_builder.builder.geofabrik import Region
    from development.maps.build_regional_buildings import michigan_region
    region=Region(region_id,'Michigan',None,
        'https://download.geofabrik.de/north-america/us/michigan-latest.osm.pbf')
    assert michigan_region([region]) is region
    with pytest.raises(ValueError,match='official Michigan'):
        michigan_region([])
