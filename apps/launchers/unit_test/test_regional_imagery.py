"""Regional export assembly and interrupted-download recovery without USGS."""

import hashlib
import json
from unittest.mock import Mock

from PIL import Image
import pytest

from development.maps import regional_imagery
from apps.launchers.local_imagery_pack import LocalImageryPack


def test_overview_resumes_checked_tiles_and_preserves_north_first_placement(tmp_path, monkeypatch):
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
                    'width':512, 'height':384, 'title':'fixture', 'attribution':'USGS fixture',
                    'sha256':hashlib.sha256((tile/'imagery.jpg').read_bytes()).hexdigest(),
                    'source_records':[{'OBJECTID': row*4+col}]}
        (tile/'manifest.json').write_text(json.dumps(document))

    allow_completion = [False]
    monkeypatch.setattr(regional_imagery, 'download_image', tile_download)
    with pytest.raises(RuntimeError, match='timed out'):
        regional_imagery.download(destination, bounds=bounds, title='Metro', cache_directory=cache)
    assert not destination.exists()
    assert (cache/'r0-c0'/'imagery.jpg').exists()
    allow_completion[0] = True
    regional_imagery.download(destination, bounds=bounds, title='Metro', cache_directory=cache)
    assert len(downloaded) == 16  # First two pieces were reused, not downloaded twice.
    pack = LocalImageryPack.load(destination)
    with Image.open(pack.image) as image:
        assert image.size == (2048,1536)
        assert image.getpixel((256,192))[0] < 5
        assert image.getpixel((256,1344))[0] > 200
        assert image.getpixel((1792,192))[1] > 200
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
