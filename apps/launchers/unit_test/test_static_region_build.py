"""Regional catalog completeness, source cache isolation and existing pack formats."""

import json
from pathlib import Path
import shutil

import pytest

from development.maps import static_region_sources as sources
from development.maps import static_region_build as builder
from development.maps.static_tile_trial import command
from development.maps.terrain_regions import MICHIGAN_SHARDS
from apps.launchers.local_terrain_pack import load_terrain
from apps.launchers.local_imagery_pack import LocalImageryPack


def item(date, tile='m_4208324_sw_17', box=(-84,42,-83,43)):
    return dict(collection='naip', properties={'datetime':date+'T00:00:00Z'}, bbox=box,
                assets={'image':{'href':f'https://naipeuwest.blob.core.windows.net/naip/{tile}_060_{date.replace("-", "")}.tif'}})


def test_paginated_naip_selects_newest_tile_across_slight_footprint_changes():
    calls=[]
    def fetch(url, **kwargs):
        calls.append((url,kwargs))
        if url.endswith('/collections/naip'):
            return {'providers':[{'name':'USDA','roles':['licensor']}]}
        if len(calls)==2:
            return dict(features=[item('2020-07-01')], links=[dict(rel='next',href=sources.PC+'/stac/v1/search?token=page2')])
        return dict(features=[item('2022-07-30',box=(-84.00001,42,-83,43))])
    records=sources.discover_imagery((-84,42,-83,43),fetch)
    assert len(records)==1 and records[0]['date'].startswith('2022')
    assert len(calls)==3


def test_unapproved_and_looping_catalog_pagination_fail_closed():
    def fetch(url,**kwargs):
        if url.endswith('/collections/naip'):
            return {'providers':[{'name':'USDA','roles':['licensor']}]}
        return dict(features=[item('2022-07-30')],links=[dict(rel='next',href='https://other.example/search')])
    with pytest.raises(ValueError,match='pagination'):
        sources.discover_imagery((-84,42,-83,43),fetch)
    def repeated(url,**kwargs):
        if url.endswith('/collections/naip'):return fetch(url)
        return dict(features=[],links=[dict(rel='next',href=sources.PC+'/stac/v1/search')])
    with pytest.raises(ValueError,match='Repeated'):
        sources.discover_imagery((-84,42,-83,43),repeated)


def test_terrain_catalog_selects_multiple_files_and_follows_offsets():
    calls=[]
    def fetch(url,**parameters):
        calls.append(parameters['offset'])
        return dict(total=101,items=[dict(boundingBox=dict(minX=-84,minY=42,maxX=-83,maxY=43),
            downloadURL='https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/a.tif',
            lastUpdated=str(parameters['offset']))]* (100 if parameters['offset']==0 else 1))
    records=sources.discover_terrain((-84,42,-83,43),fetch)
    assert calls==[0,100] and len(records)==1
    assert records[0]['date']=='100'


def test_crops_align_to_output_grid_and_reject_disjoint_sources():
    extent,size=sources.crop_spec((.25,.25,.5,.5),(0,0,1,1),100)
    assert extent==pytest.approx((.25,.25,.5,.5))
    assert size==(25,25)
    with pytest.raises(ValueError,match='intersect'):
        sources.crop_spec((2,2,3,3),(0,0,1,1),100)


def test_source_crop_cache_is_checked_and_scoped_to_bounds(tmp_path,monkeypatch):
    calls=[]
    def fake_command(*args):
        calls.append(args)
        Path(args[-1]).write_bytes(b'crop')
    monkeypatch.setattr(sources,'command',fake_command)
    monkeypatch.setattr(sources,'source_request_url',lambda url:url)
    source=dict(url='https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/a.tif',bounds_deg=(0,0,2,2))
    first,_=sources.crop_source(source,tmp_path,(0,0,1,1),100,'terrain')
    assert sources.crop_source(source,tmp_path,(0,0,1,1),100,'terrain')[0]==first
    assert len(calls)==1
    second,_=sources.crop_source(source,tmp_path,(1,1,2,2),100,'terrain')
    assert second!=first and len(calls)==2
    first.write_bytes(b'bad')
    sources.crop_source(source,tmp_path,(0,0,1,1),100,'terrain')
    assert len(calls)==3


def test_shared_tile_edges_and_missing_samples_are_not_fabricated(tmp_path):
    size=1025
    heights=[200.0]*(size*size)
    heights[0]=-9999
    records,gaps=builder.split_terrain(heights,size,tmp_path,'mi-lower-southeast')
    assert len(records)==63 and [gap['id'] for gap in gaps]==['r0-c0']
    first=json.loads((tmp_path/'r1-c0/terrain.json').read_text())
    adjacent=json.loads((tmp_path/'r1-c1/terrain.json').read_text())
    assert first['heights_m'][128::129]==adjacent['heights_m'][::129]
    assert not (tmp_path/'r0-c0').exists()


def test_staged_region_packs_load_in_existing_readers(tmp_path):
    if not shutil.which('gdal_create'):
        pytest.skip('GDAL is only required on build host')
    from PIL import Image
    coverage='mi-lower-southeast'
    west,south,east,north=MICHIGAN_SHARDS[coverage][1]
    rgb=tmp_path/'rgb.tif';dem=tmp_path/'dem.tif'
    command('gdal_create','-of','GTiff','-outsize',16,16,'-bands',4,
            '-burn',80,'-burn',120,'-burn',160,'-burn',255,
            '-a_srs','EPSG:4326','-a_ullr',west,north,east,south,rgb)
    image,info=builder.imagery_pack(tmp_path,coverage,[],[rgb],pixels=64)
    assert info['usable_pixel_fraction']==1
    assert LocalImageryPack.load(image).image.is_file()
    with Image.open(image/'imagery.webp') as picture:
        assert picture.size==(64,64)
    # Cover a margin around region endpoints, as cropped DEM sources do.
    command('gdal_create','-of','GTiff','-outsize',32,32,'-bands',1,'-ot','Float32',
            '-burn',200,'-a_srs','EPSG:4326','-a_ullr',west-.1,north+.1,east+.1,south-.1,dem)
    terrain,info=builder.terrain_pack(tmp_path,coverage,[],[dem])
    assert info['terrain_tiles']==64 and not info['missing_terrain_tiles']
    assert len(load_terrain(terrain).tiles)==64
