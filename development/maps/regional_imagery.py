"""Resumable regional overview exports, combined into the existing imagery format."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from PIL import Image

from apps.launchers.local_imagery_pack import LocalImageryPack
from development.maps.download_detroit_imagery import MAX_BYTES, download as download_image


def download(destination, *, bounds, title, cache_directory):
    # Keep large exports away from ImageServer: each request covers one sixteenth
    # of the envelope and produces one sixteenth of the final pixel count.
    cache = Path(cache_directory)
    cache.mkdir(parents=True, exist_ok=True)
    west, south, east, north = bounds
    manifests = []
    with Image.new('RGB', (2048, 1536)) as overview:
        for row in range(4):
            for column in range(4):
                tile_bounds = (west+(east-west)*column/4, north-(north-south)*(row+1)/4,
                               west+(east-west)*(column+1)/4, north-(north-south)*row/4)
                tile = cache/f'r{row}-c{column}'
                print(f'Overview image {row*4+column+1}/16 · {len(manifests)*100/16:.0f}% tiles complete', flush=True)
                if tile.exists():
                    manifest = json.loads((tile/'manifest.json').read_text())
                    if (len(manifest['bounds_deg']) != 4
                            or any(abs(a-b) > .000001 for a,b in zip(manifest['bounds_deg'], tile_bounds))
                            or (manifest['width'], manifest['height']) != (512, 384)):
                        raise ValueError('Resume tile does not match the requested overview')
                download_image(tile, bounds=tile_bounds, title=title,
                               image_size=(512,384), max_bytes=MAX_BYTES//16)
                pack = LocalImageryPack.load(tile)
                manifest = json.loads((tile/'manifest.json').read_text())
                if pack.image.stat().st_size > MAX_BYTES//16:
                    raise ValueError('Resume image exceeds the tile payload limit')
                with Image.open(pack.image) as image:
                    if image.size != (512,384):
                        raise ValueError('Overview tile has unexpected JPEG dimensions')
                    overview.paste(image.convert('RGB'), (column*512, row*384))
                manifests.append(manifest)
        print('Overview: 16/16 tiles · 100% · combining and validating…', flush=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=destination.parent, prefix='.overview-') as temporary:
            prepared = Path(temporary)/'pack'
            prepared.mkdir()
            output = prepared/'imagery.jpg'
            overview.save(output, format='JPEG', quality=90)
            records = [record for manifest in manifests for record in manifest['source_records']]
            attribution = ' · '.join(dict.fromkeys(manifest['attribution'] for manifest in manifests))
            manifest = {'schema':1, 'image':'imagery.jpg', 'title':title+' NAIP overview',
                        'bounds_deg':bounds, 'width':2048, 'height':1536, 'attribution':attribution,
                        'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                        'source_records':records, 'downloaded_at':datetime.now(timezone.utc).isoformat(),
                        'assembly':'4×4 north-first bounded exports; source years may differ by tile',
                        'bytes':output.stat().st_size}
            (prepared/'manifest.json').write_text(json.dumps(manifest, indent=2))
            for tile in sorted(cache.iterdir()):
                if tile.is_dir():
                    evidence = prepared/'sources'/tile.name
                    evidence.mkdir(parents=True)
                    for source in tile.glob('*.json'):
                        shutil.copy2(source, evidence/source.name)
            LocalImageryPack.load(prepared)
            prepared.rename(destination)
    # Completed installs do not reuse stale acquisitions on the next --update.
    # Failed/interrupted downloads retain completed, checked tiles for retry.
    shutil.rmtree(cache)
