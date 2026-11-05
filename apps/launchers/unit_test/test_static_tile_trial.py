"""Fail closed on unreviewed sources and exercise the existing pack contract."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest
from development.maps.static_tile_trial import (BOUNDS, approved_url, select_imagery,
                                                select_dem, download_source, process)
from apps.launchers.local_imagery_pack import LocalImageryPack
from apps.launchers.local_terrain_pack import load_terrain


def feature(year,url,name='NAIP Michigan'):
    return {'attributes':{'Year':year,'download_url':url,'Name':name}}


URL='https://prd-tnm.s3.amazonaws.com/StagedProducts/NAIP/MI/test.jp2'


def test_source_selection_locks_year_and_rejects_incomplete_catalogs():
    catalog={'features':[feature(2020,URL+'old'),feature(2022,URL),feature(2022,URL)]}
    assert [item['url'] for item in select_imagery(catalog)]==[URL]
    with pytest.raises(ValueError,match='incomplete'):
        select_imagery({**catalog,'exceededTransferLimit':True})
    with pytest.raises(ValueError,match='No dated'):
        select_imagery({'features':[feature(None,URL)]})
    with pytest.raises(ValueError):approved_url('https://unreviewed.example/tile.tif')
    with pytest.raises(ValueError):approved_url('http://prd-tnm.s3.amazonaws.com/StagedProducts/test.tif')


def test_terrain_source_must_contain_whole_trial_coverage():
    item={'boundingBox':{'minX':-84,'minY':42,'maxX':-83,'maxY':43},
          'downloadURL':'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/test.tif'}
    assert select_dem({'items':[item]})['url']==item['downloadURL']
    with pytest.raises(ValueError):select_dem({'items':[{**item,'boundingBox':{}}]})


def test_checked_source_cache_avoids_network_and_detects_tampering(tmp_path,monkeypatch):
    import hashlib
    from io import BytesIO
    from development.maps import static_tile_trial as module
    class Response(BytesIO):
        headers={'Content-Length':'4','ETag':'fixture'}
        def geturl(self):return URL
    calls=[]
    def fetch(*args,**kwargs):
        calls.append(args);return Response(b'tile')
    monkeypatch.setattr(module,'urlopen',fetch)
    first,receipt=download_source(URL,tmp_path,10)
    assert receipt['sha256']==hashlib.sha256(b'tile').hexdigest()
    assert download_source(URL,tmp_path,10)[0]==first
    assert len(calls)==1
    first.write_bytes(b'evil')
    download_source(URL,tmp_path,10)
    assert len(calls)==2
    with pytest.raises(ValueError,match='cap'):download_source(URL,tmp_path,2)


def test_staged_rasters_produce_existing_installable_pack_format(tmp_path):
    if not shutil.which('gdal_create') or not shutil.which('gdalwarp'):
        pytest.skip('GDAL build-host tools unavailable')
    image=tmp_path/'rgb.tif';dem=tmp_path/'dem.tif'
    west,south,east,north=BOUNDS
    subprocess.run(['gdal_create','-of','GTiff','-outsize','16','16','-bands','3',
                    '-burn','80','-burn','120','-burn','160','-a_srs','EPSG:4326',
                    '-a_ullr',str(west),str(north),str(east),str(south),str(image)],check=True)
    subprocess.run(['gdal_create','-of','GTiff','-outsize','16','16','-bands','1','-ot','Float32',
                    '-burn','200','-a_srs','EPSG:4326','-a_ullr','-84','43','-83','42',str(dem)],check=True)
    output=tmp_path/'output';output.mkdir()
    report=process({'imagery':[],'terrain':[]},{'imagery':[image],'terrain':[dem]},output)
    assert report['terrain_range_m']==[200,200]
    assert LocalImageryPack.load(output/'rochester-imagery').image.is_file()
    terrain=load_terrain(output/'rochester-terrain')
    assert terrain.width==129 and len(terrain.heights_m)==129*129
    for kind in ('imagery','terrain'):
        descriptor=json.loads((output/f'rochester-{kind}.zip.json').read_text())
        assert descriptor['coverage']=='rochester'
        assert descriptor['build_revision']=='static-source-trial-v1'


def test_landing_page_resolves_only_names_verified_in_staged_directory(monkeypatch):
    from io import BytesIO
    from development.maps import static_tile_trial as module
    name='m_4208310_se_17_060_20220715'
    key=f'StagedProducts/NAIP/mi_2022/42083/{name}_20230101.jp2'
    xml=f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>false</IsTruncated><Contents><Key>{key}</Key></Contents></ListBucketResult>'
    monkeypatch.setattr(module,'urlopen',lambda *args,**kwargs:BytesIO(xml.encode()))
    record={'Year':2022,'Name':name,'download_url':'https://earthexplorer.usgs.gov/download/options/naip/1'}
    assert module.staged_imagery_url(record)=='https://prd-tnm.s3.amazonaws.com/'+key
    with pytest.raises(ValueError,match='recognizable'):
        module.staged_imagery_url({**record,'Name':'unknown'})


def test_public_mirror_selects_dated_naip_and_keeps_unsigned_source_identity(monkeypatch):
    from development.maps import static_tile_trial as module
    url='https://naipeuwest.blob.core.windows.net/naip/mi/2022/tile.tif'
    collection={'providers':[{'name':'USDA Farm Service Agency','roles':['producer','licensor']}]}
    catalog={'features':[{'id':'mi-fixture','collection':'naip','properties':{'datetime':'2022-07-30T00:00:00Z'},
                         'assets':{'image':{'href':url}}}]}
    monkeypatch.setattr(module,'get_json',lambda address,**kwargs:collection if address.endswith('/collections/naip') else catalog)
    selected,evidence=module.planetary_imagery()
    assert selected[0]['url']==url and '?' not in selected[0]['url']
    assert evidence['collection']==collection
    monkeypatch.setattr(module,'get_json',lambda *args,**kwargs:{'href':url+'?sig=fixture'})
    assert module.source_request_url(url)==url+'?sig=fixture'
    monkeypatch.setattr(module,'get_json',lambda *args,**kwargs:{'href':'https://other.example/tile.tif?sig=fixture'})
    with pytest.raises(ValueError,match='changed'):module.source_request_url(url)


def test_gdal_failures_and_timeouts_do_not_expose_temporary_access_urls(monkeypatch):
    from types import SimpleNamespace
    from development.maps import static_tile_trial as module
    url='https://naipeuwest.blob.core.windows.net/naip/tile.tif?sig=fixture-secret'
    monkeypatch.setattr(module.subprocess,'run',lambda *args,**kwargs:SimpleNamespace(returncode=1,stderr='failed '+url))
    with pytest.raises(RuntimeError) as failure:module.command('gdalwarp',url)
    assert 'fixture-secret' not in str(failure.value)
    assert '[redacted]' in str(failure.value)


def test_alpha_padded_cog_crops_mosaic_without_hiding_adjacent_tile(tmp_path):
    if not shutil.which('gdal_create') or not shutil.which('gdalwarp'):
        pytest.skip('GDAL build-host tools unavailable')
    from PIL import Image
    from development.maps.static_tile_trial import command
    west,south,east,north=BOUNDS
    split=(west+east)/2
    crops=[]
    for index,(left,right,color) in enumerate(((west,split,80),(split,east,160))):
        source=tmp_path/f'part-{index}.tif';crop=tmp_path/f'crop-{index}.tif'
        command('gdal_create','-of','GTiff','-outsize','16','16','-bands','3','-burn',color,
                '-a_srs','EPSG:4326','-a_ullr',left,north,right,south,source)
        command('gdalwarp','-overwrite','-t_srs','EPSG:4326','-te',*BOUNDS,
                '-ts','64','64','-dstalpha',source,crop)
        crops.append(crop)
    dem=tmp_path/'dem.tif'
    command('gdal_create','-of','GTiff','-outsize','16','16','-bands','1','-ot','Float32',
            '-burn','200','-a_srs','EPSG:4326','-a_ullr','-84','43','-83','42',dem)
    output=tmp_path/'output';output.mkdir()
    process({'imagery':[],'terrain':[]},{'imagery':crops,'terrain':[dem]},output)
    with Image.open(output/'rochester-imagery/imagery.jpg') as image:
        assert 75<image.getpixel((1000,2000))[0]<85
        assert 155<image.getpixel((3000,2000))[0]<165
