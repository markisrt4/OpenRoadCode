"""Bounded catalog discovery and resumable raster crops for regional builds."""

import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

from development.maps.static_tile_trial import (
    PC, TNM, approved_url, command, digest, get_json, source_request_url, write_json,
)


def intersect(a, b):
    result = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
    return result if result[0] < result[2] and result[1] < result[3] else None


def discover_imagery(bounds, fetch=get_json):
    """Follow bounded STAC pages; retain newest dated NAIP per source footprint."""
    collection = fetch(PC + '/stac/v1/collections/naip')
    if not any('USDA' in p.get('name', '') and 'licensor' in p.get('roles', [])
               for p in collection.get('providers', [])):
        raise ValueError('NAIP collection must identify USDA as licensor')
    url = PC + '/stac/v1/search'
    parameters = dict(collections='naip', bbox=','.join(map(str, bounds)), limit=100)
    seen = set()
    selected = {}
    for _ in range(100):
        key = (url, json.dumps(parameters, sort_keys=True))
        if key in seen:
            raise ValueError('Repeated NAIP catalog page')
        seen.add(key)
        page = fetch(url, **parameters)
        for item in page.get('features', []):
            date = item.get('properties', {}).get('datetime') or item.get('properties', {}).get('start_datetime', '')
            if item.get('collection') != 'naip' or len(date) < 10 or not date[:4].isdigit():
                raise ValueError('Unexpected or undated NAIP source')
            box = item.get('bbox', [])
            if len(box) != 4 or not intersect(bounds, box):
                continue
            address = approved_url(item['assets']['image']['href'])
            if urlsplit(address).hostname != 'naipeuwest.blob.core.windows.net':
                raise ValueError('Unexpected NAIP mirror')
            tile = re.match(r'(m_[0-9]{7}_[a-z]{2}_[0-9]{2})_', Path(urlsplit(address).path).name)
            footprint = tile[1] if tile else tuple(round(v, 5) for v in box)
            record = dict(url=address, bounds_deg=box, date=date, record=item)
            if date > selected.get(footprint, {}).get('date', ''):
                selected[footprint] = record
        links = [link for link in page.get('links', []) if link.get('rel') == 'next']
        if not links:
            break
        link = links[0]
        url = link['href']
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.hostname != 'planetarycomputer.microsoft.com'
                or parsed.path != '/api/stac/v1/search' or link.get('method', 'GET') != 'GET'):
            raise ValueError('Unapproved NAIP pagination link')
        parameters = {}
    else:
        raise ValueError('NAIP catalog exceeds 100-page build limit')
    result = sorted(selected.values(), key=lambda item: (item['date'], item['url']))
    if not result:
        raise ValueError('No dated NAIP files in regional catalog')
    return result


def discover_terrain(bounds, fetch=get_json):
    selected = {}
    for offset in range(0, 2000, 100):
        page = fetch(TNM, bbox=','.join(map(str, bounds)),
                     datasets='National Elevation Dataset (NED) 1/3 arc-second',
                     max=100, offset=offset, outputFormat='JSON')
        items = page.get('items', [])
        for item in items:
            box = item.get('boundingBox', {})
            box = [box.get(k) for k in ('minX', 'minY', 'maxX', 'maxY')]
            if any(v is None for v in box) or not intersect(bounds, box):
                continue
            url = item.get('downloadURL', '')
            if not url.lower().endswith('.tif'):
                continue
            url = approved_url(url)
            date = str(item.get('lastUpdated') or item.get('publicationDate') or '')
            footprint = tuple(round(v, 5) for v in box)
            if date >= selected.get(footprint, {}).get('date', ''):
                selected[footprint] = dict(url=url, bounds_deg=box, date=date, record=item)
        total = int(page.get('total', len(items)))
        if offset + len(items) >= total:
            break
        if not items:
            raise ValueError('Incomplete terrain catalog pagination')
    else:
        raise ValueError('Terrain catalog exceeds 2000-record limit')
    if not selected:
        raise ValueError('No staged 3DEP files in regional catalog')
    return sorted(selected.values(), key=lambda item: (item['date'], item['url']))


def crop_spec(source_bounds, bounds, size):
    """Align each small source crop to the final raster pixel lattice."""
    overlap = intersect(source_bounds, bounds)
    if overlap is None:
        raise ValueError('Source does not intersect output grid')
    west, south, east, north = bounds
    dx, dy = (east-west)/size, (north-south)/size
    left = max(0, math.floor((overlap[0]-west)/dx))
    right = min(size, math.ceil((overlap[2]-west)/dx))
    top = max(0, math.floor((north-overlap[3])/dy))
    bottom = min(size, math.ceil((north-overlap[1])/dy))
    return (west+left*dx, north-bottom*dy, west+right*dx, north-top*dy), (right-left, bottom-top)


def crop_source(item, cache, bounds, size, kind):
    extent, dimensions = crop_spec(item['bounds_deg'], bounds, size)
    spec = dict(url=item['url'], bounds_deg=extent, dimensions=dimensions, kind=kind, revision=1)
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    target, receipt = cache/(key+'.tif'), cache/(key+'.json')
    if target.is_file() and receipt.is_file():
        saved = json.loads(receipt.read_text())
        if saved['sha256'] == digest(target) and saved['spec'] == json.loads(json.dumps(spec)):
            return target, saved
    temporary = cache/(key+'.part.tif')
    options = ('-srcband', '1', '-srcband', '2', '-srcband', '3', '-dstalpha') if kind == 'imagery' else ('-ot', 'Float32', '-dstnodata', '-9999')
    try:
        for attempt in range(3):
            try:
                command('gdalwarp', '-overwrite', '-wm', '64', '-t_srs', 'EPSG:4326',
                        '-te', *extent, '-ts', *dimensions, '-r', 'bilinear', *options,
                        '-co', 'COMPRESS=DEFLATE', '/vsicurl/'+source_request_url(item['url']), temporary)
                break
            except RuntimeError:
                if attempt == 2:
                    raise
        if temporary.stat().st_size > 64*1024*1024:
            raise ValueError('Regional source crop exceeds 64 MiB')
        saved = dict(spec=spec, sha256=digest(temporary), cached_bytes=temporary.stat().st_size,
                     transfer_note='Cached bytes are not measured network traffic')
        temporary.replace(target)
        write_json(receipt, saved)
        return target, saved
    finally:
        temporary.unlink(missing_ok=True)
