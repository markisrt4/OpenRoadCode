"""Resumable regional overview exports, combined into the existing imagery format."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from PIL import Image

from apps.launchers.local_imagery_pack import LocalImageryPack
from development.maps.download_detroit_imagery import MAX_BYTES, NoImageryCoverage, download as download_image


def download(destination, *, bounds, title, cache_directory, image_size=(2048,1536)):
    # Keep large exports away from ImageServer: each request covers one sixteenth
    # of the envelope and produces one sixteenth of the final pixel count.
    if image_size not in ((2048,1536), (4096,4096)):
        raise ValueError('Unsupported regional image dimensions')
    if destination.exists():
        LocalImageryPack.load(destination)
        existing = json.loads((destination/'manifest.json').read_text())
        if (existing['width'], existing['height']) != image_size or existing['bounds_deg'] != list(bounds):
            raise ValueError('Existing build has different dimensions or coverage; choose a new output directory')
        print(f'Validated build already exists: {destination}')
        return
    tile_size = (image_size[0]//4, image_size[1]//4)
    cache = Path(cache_directory)
    cache.mkdir(parents=True, exist_ok=True)
    west, south, east, north = bounds
    manifests = []
    gaps = []
    with Image.new('RGBA', image_size, (0,0,0,0)) as overview:
        for row in range(4):
            for column in range(4):
                tile_bounds = (west+(east-west)*column/4, north-(north-south)*(row+1)/4,
                               west+(east-west)*(column+1)/4, north-(north-south)*row/4)
                tile = cache/f'r{row}-c{column}'
                print(f'Overview image {row*4+column+1}/16 · {(len(manifests)+len(gaps))*100/16:.0f}% tiles complete', flush=True)
                missing = tile/'no-coverage.json'
                if missing.exists():
                    gap = json.loads(missing.read_text())
                    if gap['bounds_deg'] != list(tile_bounds):
                        raise ValueError('Cached coverage gap does not match the requested overview')
                    gaps.append(gap)
                    print(f'{tile.name}: no NAIP coverage; leaving this area transparent.', flush=True)
                    continue
                if tile.exists():
                    manifest = json.loads((tile/'manifest.json').read_text())
                    if (len(manifest['bounds_deg']) != 4
                            or any(abs(a-b) > .000001 for a,b in zip(manifest['bounds_deg'], tile_bounds))
                            or (manifest['width'], manifest['height']) != tile_size):
                        raise ValueError('Resume tile does not match the requested overview')
                try:
                    download_image(tile, bounds=tile_bounds, title=title,
                                   image_size=tile_size, max_bytes=MAX_BYTES//16)
                except NoImageryCoverage as error:
                    gap = {'bounds_deg':tile_bounds, 'reason':'No approved NAIP/USDA source in complete catalog'}
                    with TemporaryDirectory(dir=cache, prefix='.gap-') as temporary:
                        prepared = Path(temporary)/'tile'
                        prepared.mkdir()
                        (prepared/'no-coverage.json').write_text(json.dumps(gap))
                        (prepared/'source-service.json').write_text(json.dumps(error.metadata))
                        (prepared/'source-catalog.json').write_text(json.dumps(error.catalog))
                        prepared.rename(tile)
                    gaps.append(gap)
                    print(f'{tile.name}: no NAIP coverage; leaving this area transparent.', flush=True)
                    continue
                pack = LocalImageryPack.load(tile)
                manifest = json.loads((tile/'manifest.json').read_text())
                if pack.image.stat().st_size > MAX_BYTES//16:
                    raise ValueError('Resume image exceeds the tile payload limit')
                with Image.open(pack.image) as image:
                    if image.size != tile_size:
                        raise ValueError('Overview tile has unexpected JPEG dimensions')
                    overview.paste(image.convert('RGB'), (column*tile_size[0], row*tile_size[1]))
                manifests.append(manifest)
        if not manifests:
            raise ValueError('No supported NAIP imagery anywhere in the selected region')
        print(f'Overview: 16/16 areas checked · 100% · {len(gaps)} coverage gaps · combining and validating…', flush=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=destination.parent, prefix='.overview-') as temporary:
            prepared = Path(temporary)/'pack'
            prepared.mkdir()
            output = prepared/('imagery.png' if gaps else 'imagery.jpg')
            if gaps:
                overview.save(output, format='PNG')
            else:
                with overview.convert('RGB') as opaque:
                    opaque.save(output, format='JPEG', quality=90)
            records = [record for manifest in manifests for record in manifest['source_records']]
            attribution = ' · '.join(dict.fromkeys(manifest['attribution'] for manifest in manifests))
            suffix = f' · {len(gaps)} coverage gaps' if gaps else ''
            manifest = {'schema':1, 'image':output.name, 'title':title+' NAIP '+('detail' if image_size == (4096,4096) else 'overview')+suffix,
                        'bounds_deg':bounds, 'width':image_size[0], 'height':image_size[1], 'attribution':attribution,
                        'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                        'source_records':records, 'downloaded_at':datetime.now(timezone.utc).isoformat(),
                        'assembly':'4×4 north-first bounded exports; source years may differ by tile',
                        'bytes':output.stat().st_size, 'missing_coverage':gaps}
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
