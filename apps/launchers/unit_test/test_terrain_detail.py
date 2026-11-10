"""Bounded detail grids, legacy terrain routing and real GDAL archive contracts."""
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from development.maps.build_terrain_detail import grid_definition
from development.maps.detail_coverages import TERRAIN_DETAILS
from development.maps.static_region_build import terrain_pack
from development.maps.static_tile_trial import command
from apps.launchers import local_terrain_pack as runtime
from development.maps import install_terrain as installer


@pytest.mark.parametrize('bounds',[bounds for _,bounds in TERRAIN_DETAILS.values()])
def test_pilot_grid_stays_within_existing_64_children_and_ten_metre_sampling(bounds):
    divisions,spacing=grid_definition(bounds)
    assert 1<=divisions<=8
    assert 0<spacing['latitude_m']<=10 and 0<spacing['longitude_m']<=10
    assert divisions**2<=64


def test_large_coverage_cannot_be_silently_downsampled_or_exceed_tile_budget():
    with pytest.raises(ValueError,match='too large'):grid_definition((-84,42,-82,44))


def test_michigan_terrain_install_uses_terrain_bounds_and_active_directory(tmp_path,monkeypatch):
    from development.maps.terrain_regions import MICHIGAN_COVERAGES
    key='mi-lower-southwest'
    monkeypatch.setattr('sys.argv',['install_terrain','--coverage',key,'--pack-file','fake.zip','--yes'])
    monkeypatch.setattr(installer,'regional_terrain_directory',lambda k:tmp_path/(k+'-terrain-active'))
    monkeypatch.setattr(installer,'read_local_archive',lambda *args:({'kind':'terrain'},Path('fake.zip')))
    monkeypatch.setattr(installer,'verify_archive',Mock())
    activate=Mock();monkeypatch.setattr(installer,'_install_archive',activate)
    monkeypatch.setattr(installer,'load_terrain',lambda path:SimpleNamespace(width=129,height=129))
    assert installer.main()==0
    assert activate.call_args.args[1].name==key+'-terrain-active'
    assert activate.call_args.kwargs['expected_bounds']==MICHIGAN_COVERAGES[key][1]


def test_gdal_detail_grid_packages_installs_and_gets_local_catalog_priority(tmp_path,monkeypatch):
    if not shutil.which('gdal_create'):pytest.skip('Build-host GDAL dependency')
    from tools.map_builder.builder.terrain_artifact import package
    key='detroit-midtown-detail-10m';title,bounds=TERRAIN_DETAILS[key]
    w,s,e,n=bounds;dx,dy=(e-w)/128,(n-s)/128
    source=tmp_path/'dem.tif'
    command('gdal_create','-of','GTiff','-outsize',32,32,'-bands',1,'-ot','Float32','-burn',230,
            '-a_srs','EPSG:4326','-a_ullr',w-dx,n+dy,e+dx,s-dy,source)
    pack,metrics=terrain_pack(tmp_path,key,[],[source],bounds=bounds,title=title,divisions=1)
    manifest=json.loads((pack/'manifest.json').read_text())
    for tile in manifest['tiles']:tile.update(detail_level=5,minimum_zoom=13)
    manifest['maximum_zoom']=16
    (pack/'manifest.json').write_text(json.dumps(manifest))
    assert metrics['missing_terrain_tiles']==[]
    assert all(h==pytest.approx(230) for h in runtime.load_terrain(pack).tiles[0].heights_m)
    archive=tmp_path/(key+'-terrain.zip');package(pack,archive,key)
    active=tmp_path/'device'/(key+'-terrain-active')
    installer._install_archive(archive,active,expected_bounds=bounds)
    previous=active.resolve()
    with pytest.raises(ValueError,match='bounds'):
        installer._install_archive(archive,active,expected_bounds=(-84,42,-83,43))
    assert active.resolve()==previous
    monkeypatch.setattr(runtime,'openroadcode_data_dir',lambda *parts:tmp_path/'device')
    catalog=runtime.load_installed_terrain_catalog()
    assert catalog.state.maximum_zoom==16
    assert len(catalog.state.tiles)==1
    assert catalog.state.tiles[0].detail_level==7
    assert catalog.state.tiles[0].minimum_zoom==13
