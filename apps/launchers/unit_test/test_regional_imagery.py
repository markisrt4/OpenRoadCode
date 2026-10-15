"""Regional export assembly and interrupted-download recovery without USGS."""

import hashlib
import json
from unittest.mock import Mock

from PIL import Image
import pytest

from development.maps import regional_imagery
from apps.launchers.local_imagery_pack import LocalImageryPack


@pytest.mark.parametrize('image_size', [(2048,1536),(4096,4096)])
def test_overview_resumes_checked_tiles_and_preserves_north_first_placement(tmp_path, monkeypatch, image_size):
    bounds = (-84., 42., -82., 44.)
    cache = tmp_path/'cache'
    destination = tmp_path/'pack'
    downloaded = []

    def tile_download(tile, **parameters):
        if tile.exists():
            return
        if len(downloaded) == 2 and not allow_completion[0]:
            raise RuntimeError('export timed out')
        downloaded.append(tile.name)
        tile.mkdir()
        row = int(tile.name[1])
        col = int(tile.name[-1])
        with Image.new('RGB', parameters['image_size'], (row*70, col*70, 0)) as image:
            image.save(tile/'imagery.jpg')
        document = {'schema':1, 'image':'imagery.jpg', 'bounds_deg':parameters['bounds'],
                    'width':parameters['image_size'][0], 'height':parameters['image_size'][1], 'title':'fixture', 'attribution':'USGS fixture',
                    'sha256':hashlib.sha256((tile/'imagery.jpg').read_bytes()).hexdigest(),
                    'source_records':[{'OBJECTID': row*4+col}]}
        (tile/'manifest.json').write_text(json.dumps(document))

    allow_completion = [False]
    monkeypatch.setattr(regional_imagery, 'download_image', tile_download)
    with pytest.raises(RuntimeError, match='timed out'):
        regional_imagery.download(destination, bounds=bounds, title='Metro', cache_directory=cache, image_size=image_size)
    assert not destination.exists()
    assert (cache/'r0-c0'/'imagery.jpg').exists()
    allow_completion[0] = True
    regional_imagery.download(destination, bounds=bounds, title='Metro', cache_directory=cache, image_size=image_size)
    assert len(downloaded) == 16  # First two pieces were reused, not downloaded twice.
    pack = LocalImageryPack.load(destination)
    with Image.open(pack.image) as image:
        assert image.size == image_size
        width,height = image_size
        assert image.getpixel((width//8,height//8))[0] < 5
        assert image.getpixel((width//8,height*7//8))[0] > 200
        assert image.getpixel((width*7//8,height//8))[1] > 200
    assert len(json.loads((destination/'manifest.json').read_text())['source_records']) == 16
    assert (destination/'sources'/'r0-c0'/'manifest.json').exists()
    assert not cache.exists()


def test_overview_rejects_cache_for_other_coverage(tmp_path, monkeypatch):
    cache = tmp_path/'cache'
    tile = cache/'r0-c0'
    tile.mkdir(parents=True)
    (tile/'manifest.json').write_text(json.dumps({'bounds_deg':[0,0,1,1], 'width':512, 'height':384}))
    download = Mock()
    monkeypatch.setattr(regional_imagery, 'download_image', download)
    with pytest.raises(ValueError, match='does not match'):
        regional_imagery.download(tmp_path/'pack', bounds=(-84,42,-82,44), title='Metro', cache_directory=cache)
    download.assert_not_called()
    assert not (tmp_path/'pack').exists()


def test_unsupported_area_is_transparent_and_evidence_is_preserved(tmp_path, monkeypatch):
    bounds = (-84.,42.,-82.,44.)
    def tile_download(tile, **parameters):
        if tile.name == 'r3-c3':
            raise regional_imagery.NoImageryCoverage({'serviceDescription':'public domain'}, {'features':[]})
        tile.mkdir()
        with Image.new('RGB', (512,384), 'red') as image:
            image.save(tile/'imagery.jpg')
        (tile/'manifest.json').write_text(json.dumps({
            'schema':1,'image':'imagery.jpg','bounds_deg':parameters['bounds'],
            'width':512,'height':384,'title':'fixture','attribution':'USGS fixture',
            'sha256':hashlib.sha256((tile/'imagery.jpg').read_bytes()).hexdigest(), 'source_records':[],
        }))
    monkeypatch.setattr(regional_imagery, 'download_image', tile_download)
    regional_imagery.download(tmp_path/'pack', bounds=bounds, title='Metro', cache_directory=tmp_path/'cache')
    pack = LocalImageryPack.load(tmp_path/'pack')
    assert pack.image.suffix == '.webp'
    assert pack.image.stat().st_size <= regional_imagery.MAX_BYTES
    with Image.open(pack.image) as image:
        assert image.getpixel((1792,1344))[3] == 0
        assert image.getpixel((256,192))[3] == 255
    manifest = json.loads((tmp_path/'pack'/'manifest.json').read_text())
    assert len(manifest['missing_coverage']) == 1
    assert manifest['encoding'] == 'WebP with alpha'
    assert (tmp_path/'pack'/'sources'/'r3-c3'/'source-catalog.json').exists()
