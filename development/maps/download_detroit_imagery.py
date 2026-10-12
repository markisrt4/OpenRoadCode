"""Download a bounded USGS/USDA NAIP image once, retaining source evidence."""

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from http.client import IncompleteRead
import json
import re
import time
from urllib.error import HTTPError, URLError
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.parse
import urllib.request

from apps.launchers.local_imagery_pack import detroit_pack_directory, pine_knob_imagery_directory, LocalImageryPack
from tools.map_builder.builder.map_3d import PRESETS

SERVICE = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer"
BOUNDS = (-83.065, 42.315, -83.025, 42.345)
MAX_BYTES = 20 * 1024 * 1024
CATALOG_FIELDS = 'OBJECTID,Name,Year,raster_name,agency,vendor,download_url,acquisition_date,resolution_value,resolution_units'
CATALOG_BATCH_SIZE = 20


class SourceRequestError(RuntimeError):
    """A failed network response, distinct from invalid catalog/source data."""


def retryable(error):
    return not isinstance(error, HTTPError) or error.code in (429, 500, 502, 503, 504)


def source_catalog(bounds):
    parameters = dict(where="State='MI' AND Category=1",
                      geometry=','.join(map(str, bounds)), geometryType='esriGeometryEnvelope',
                      inSR=4326, spatialRel='esriSpatialRelIntersects', returnGeometry='false')
    catalog = get_json('/query', **parameters, outFields=CATALOG_FIELDS)
    if not catalog.get('exceededTransferLimit'):
        return catalog
    # ArcGIS ID-only queries bypass the feature response limit. Fetch explicit
    # batches rather than relying on offset pagination support on ImageServer.
    index = get_json('/query', **parameters, returnIdsOnly='true')
    identifiers = index.get('objectIds')
    if (index.get('exceededTransferLimit') or not isinstance(identifiers, list)
            or not identifiers or len(identifiers) > 10000
            or any(type(value) is not int for value in identifiers)
            or len(set(identifiers)) != len(identifiers)):
        raise RuntimeError('Cannot obtain a complete bounded imagery catalog ID list')
    print(f'USGS imagery: fetching {len(identifiers)} source records in batches…', flush=True)

    def fetch(ids):
        print(f'Catalog: requesting {len(ids)} records…', flush=True)
        try:
            document = get_json('/query', objectIds=','.join(map(str, ids)),
                                outFields=CATALOG_FIELDS, returnGeometry='false',
                                timeout=30, attempts=2 if len(ids) > 1 else None)
        except SourceRequestError as error:
            if len(ids) == 1 or not retryable(error.__cause__):
                raise
            print(f'Catalog batch failed; splitting {len(ids)} records into smaller requests.', flush=True)
            middle = len(ids)//2
            return fetch(ids[:middle]) + fetch(ids[middle:])
        if document.get('exceededTransferLimit'):
            if len(ids) == 1:
                raise RuntimeError('USGS truncated a single source record')
            middle = len(ids)//2
            return fetch(ids[:middle]) + fetch(ids[middle:])
        features = document.get('features', [])
        returned = [feature.get('attributes', {}).get('OBJECTID') for feature in features]
        if len(returned) != len(ids) or set(returned) != set(ids):
            raise RuntimeError('USGS imagery catalog batch is incomplete; retry download')
        return features

    features = []
    for offset in range(0, len(identifiers), CATALOG_BATCH_SIZE):
        features.extend(fetch(identifiers[offset:offset+CATALOG_BATCH_SIZE]))
        print(f'Catalog: {len(features):,}/{len(identifiers):,} records · '
              f'{len(features)*100/len(identifiers):.0f}%', flush=True)
    return {'features': features, 'exceededTransferLimit': False,
            'retrieval': 'bounded object-ID batches', 'source_index': index}


def read_image(response, *, max_bytes=MAX_BYTES):
    """Bounded streaming read with honest progress when total size is unknown."""
    headers = getattr(response, 'headers', {})
    raw_length = headers.get('Content-Length', '')
    try:
        total = int(raw_length)
    except (TypeError, ValueError):
        total = 0
    if total < 0:
        total = 0
    if total > max_bytes:
        raise RuntimeError(f'USGS export exceeds the {max_bytes/1024/1024:g} MiB image limit')
    content = bytearray()
    last_report = 0.0

    def report(done=False):
        size = len(content)/1024/1024
        if total:
            # Completion requires EOF and length validation, not just a header.
            percentage = 100 if done else min(99, len(content)*100/total)
            label = f'{size:.2f} / {total/1024/1024:.2f} MiB · {percentage:.0f}%'
        else:
            label = f'{size:.2f} MiB · total size unknown'
            if done:
                label += ' · complete'
        print(f'\rImagery download: {label}', end='\n' if done else '', flush=True)

    report()
    try:
        while True:
            chunk = response.read(min(64*1024, max_bytes+1-len(content)))
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > max_bytes:
                raise RuntimeError(f'USGS export exceeds the {max_bytes/1024/1024:g} MiB image limit')
            now = time.monotonic()
            if now-last_report >= .2:
                report()
                last_report = now
        if total and len(content) != total:
            raise RuntimeError('USGS image download size differs from Content-Length; retry download')
    except BaseException:
        print(flush=True)
        raise
    report(done=True)
    return bytes(content)


def wait_to_retry(error, attempt, stage):
    delay = min(120, 10*2**min(attempt-1, 4))
    header = getattr(error, 'headers', None)
    value = header.get('Retry-After') if header else None
    if value:
        try:
            requested = int(value)
        except ValueError:
            try:
                requested = int((parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                requested = 0
        delay = max(delay, requested)
    print(f'USGS {stage} failed: {error}. Retry {attempt}; Ctrl+C stops safely.', flush=True)
    for remaining in range(delay, 0, -1):
        print(f'\rRetry {attempt} in {remaining}s… ', end='', flush=True)
        time.sleep(1)
    print(flush=True)


def retry_request(operation, *, stage, attempts=None):
    attempt = 0
    while True:
        try:
            return operation()
        except (URLError, TimeoutError, IncompleteRead) as error:
            attempt += 1
            if not retryable(error) or (attempts is not None and attempt >= attempts):
                raise
            wait_to_retry(error, attempt, stage)


def open_source(url, *, timeout, attempts=None):
    return retry_request(lambda: urllib.request.urlopen(url, timeout=timeout),
                         stage='imagery connection', attempts=attempts)


def get_json(endpoint, *, timeout=60, attempts=None, **parameters):
    stage = {"":"service metadata", "/query":"NAIP source catalog", "/exportImage":"bounded image export"}.get(endpoint, endpoint)
    print(f'USGS imagery: requesting {stage}…', flush=True)
    url = SERVICE + endpoint + "?" + urllib.parse.urlencode({"f":"json", **parameters})

    def read():
        with open_source(url, timeout=timeout, attempts=1) as response:
            document = json.load(response)
        if 'error' in document:
            error = document['error']
            if error.get('code') in (429, 500, 502, 503, 504):
                raise HTTPError(url, error['code'], error.get('message', 'Service unavailable'), {}, None)
            raise RuntimeError(f'USGS service error: {error}')
        return document

    try:
        return retry_request(read, stage=stage, attempts=attempts)
    except (URLError, TimeoutError, IncompleteRead) as error:
        raise SourceRequestError(f'{stage} failed after retries: {error} · endpoint {SERVICE+endpoint}') from error


def download_image_bytes(href, max_bytes):
    def read():
        with open_source(href, timeout=90, attempts=1) as response:
            return read_image(response, max_bytes=max_bytes)
    return retry_request(read, stage='exported JPEG download')


def download(destination, *, bounds=BOUNDS, title="Detroit", image_size=(2048,1536), max_bytes=MAX_BYTES):
    if destination.exists():
        pack = LocalImageryPack.load(destination)
        print(f"Already installed: {pack.image} ({pack.image.stat().st_size:,} bytes)")
        return
    metadata = get_json("")
    if "public domain" not in metadata.get("serviceDescription", "").lower():
        raise RuntimeError("USGS service no longer declares public-domain imagery; review source rights")
    catalog = source_catalog(bounds)
    records = [feature["attributes"] for feature in catalog.get("features", [])]
    # Limit the experiment to identifiable NAIP/USDA acquisitions, not arbitrary
    # partner mosaics. Fail visibly rather than substituting another provider.
    def naip(record):
        names = (record.get("Name") or "", record.get("raster_name") or "")
        text = " ".join(str(record.get(key) or "") for key in ("Name","raster_name","agency","download_url")).lower()
        return "naip" in text or "usda" in text or any(re.match(r"m_\d{7}_[ns][ew]_", name.lower()) for name in names)
    candidates = [record for record in records if naip(record) and isinstance(record.get("Year"), int)]
    if not candidates:
        raise RuntimeError("No identifiable dated NAIP/USDA source found for selected coverage; source review required")
    year = max(record["Year"] for record in candidates)
    selected = [record for record in candidates if record["Year"] == year]
    mosaic = {"mosaicMethod":"esriMosaicLockRaster", "lockRasterIds":[r["OBJECTID"] for r in selected],
              "mosaicOperation":"MT_FIRST"}
    export = get_json("/exportImage", bbox=",".join(map(str, bounds)), bboxSR=4326, imageSR=4326,
                      size=','.join(map(str, image_size)), format="jpg", adjustAspectRatio="false",
                      mosaicRule=json.dumps(mosaic), renderingRule=json.dumps({"rasterFunction":"NaturalColor"}))
    requested_bounds = bounds
    extent = export["extent"]
    if extent.get("spatialReference", {}).get("wkid") != 4326:
        raise RuntimeError("USGS export is not geographic WGS84")
    bounds = [extent[k] for k in ("xmin","ymin","xmax","ymax")]
    if any(abs(actual-requested) > .000001 for actual,requested in zip(bounds, requested_bounds)):
        raise RuntimeError("Export coverage differs from the requested bounded area")
    if (export['width'], export['height']) != image_size:
        raise RuntimeError('Export dimensions differ from the requested image size')
    href = export["href"]
    parsed = urllib.parse.urlsplit(href)
    if parsed.scheme != "https" or parsed.hostname != "imagery.nationalmap.gov":
        raise RuntimeError("USGS export returned an unexpected download host")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="naip-imagery-", dir=destination.parent) as temporary:
        root = Path(temporary)
        print('USGS imagery: downloading exported JPEG…', flush=True)
        try:
            image = download_image_bytes(href, max_bytes)
        except (URLError, TimeoutError) as error:
            raise RuntimeError(f'exported JPEG download failed after retries: {error} · endpoint {href}') from error
        if len(image) > MAX_BYTES or not image.startswith(b"\xff\xd8"):
            raise RuntimeError("USGS export is oversized or not a JPEG image")
        (root / "imagery.jpg").write_bytes(image)
        manifest = {"schema":1, "image":"imagery.jpg", "sha256":hashlib.sha256(image).hexdigest(),
                    "title":f"{title} NAIP {year}", "attribution":f"USGS / USDA NAIP {year} · The National Map",
                    "bounds_deg":bounds, "width":export["width"], "height":export["height"],
                    "source":SERVICE, "source_records":selected, "downloaded_at":datetime.now(timezone.utc).isoformat(),
                    "rights":"Public-domain NAIP imagery; USGS service description retained in source-service.json",
                    "rights_reference":SERVICE, "bytes":len(image)}
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (root / "source-service.json").write_text(json.dumps(metadata, indent=2))
        (root / "source-catalog.json").write_text(json.dumps(catalog, indent=2))
        (root / "export.json").write_text(json.dumps(export, indent=2))
        LocalImageryPack.load(root)
        root.rename(destination)
    print(f"Installed {manifest['title']}: {len(image):,} image bytes at {destination}")
    print("Inspect the image for coverage/no-data gaps; export pixels are not proof of native source resolution.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--coverage", choices=("detroit-downtown", "pine-knob"), default="detroit-downtown")
    args = parser.parse_args()
    try:
        title, bounds = PRESETS[args.coverage]
        destination = args.output or (pine_knob_imagery_directory() if args.coverage == "pine-knob" else detroit_pack_directory())
        print(f"Downloading {title} NAIP imagery · maximum image size 20 MiB", flush=True)
        download(destination, bounds=bounds, title="Pine Knob" if args.coverage == "pine-knob" else "Detroit")
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        parser.exit(1, f"Imagery download: {error}\n")


if __name__ == "__main__":
    main()
