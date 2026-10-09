"""Download a bounded USGS/USDA NAIP image once, retaining source evidence."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.parse
import urllib.request

from apps.launchers.local_imagery_pack import detroit_pack_directory, LocalImageryPack

SERVICE = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer"
BOUNDS = (-83.065, 42.315, -83.025, 42.345)
MAX_BYTES = 20 * 1024 * 1024


def get_json(endpoint, **parameters):
    url = SERVICE + endpoint + "?" + urllib.parse.urlencode({"f":"json", **parameters})
    with urllib.request.urlopen(url, timeout=60) as response:
        document = json.load(response)
    if "error" in document:
        raise RuntimeError(f"USGS service error: {document['error']}")
    return document


def download(destination, *, bounds=BOUNDS):
    if destination.exists():
        pack = LocalImageryPack.load(destination)
        print(f"Already installed: {pack.image} ({pack.image.stat().st_size:,} bytes)")
        return
    metadata = get_json("")
    if "public domain" not in metadata.get("serviceDescription", "").lower():
        raise RuntimeError("USGS service no longer declares public-domain imagery; review source rights")
    catalog = get_json("/query", where="State='MI' AND Category=1",
                       geometry=",".join(map(str, bounds)), geometryType="esriGeometryEnvelope",
                       inSR=4326, spatialRel="esriSpatialRelIntersects", returnGeometry="false",
                       outFields="OBJECTID,Name,Year,raster_name,agency,vendor,download_url,acquisition_date,resolution_value,resolution_units")
    if catalog.get("exceededTransferLimit"):
        raise RuntimeError("Catalog result is truncated; narrow the dataset query")
    records = [feature["attributes"] for feature in catalog.get("features", [])]
    # Limit the experiment to identifiable NAIP/USDA acquisitions, not arbitrary
    # partner mosaics. Fail visibly rather than substituting another provider.
    def naip(record):
        names = (record.get("Name") or "", record.get("raster_name") or "")
        text = " ".join(str(record.get(key) or "") for key in ("Name","raster_name","agency","download_url")).lower()
        return "naip" in text or "usda" in text or any(re.match(r"m_\d{7}_[ns][ew]_", name.lower()) for name in names)
    candidates = [record for record in records if naip(record) and isinstance(record.get("Year"), int)]
    if not candidates:
        raise RuntimeError("No identifiable dated NAIP/USDA source found for Detroit; source review required")
    year = max(record["Year"] for record in candidates)
    selected = [record for record in candidates if record["Year"] == year]
    mosaic = {"mosaicMethod":"esriMosaicLockRaster", "lockRasterIds":[r["OBJECTID"] for r in selected],
              "mosaicOperation":"MT_FIRST"}
    export = get_json("/exportImage", bbox=",".join(map(str, bounds)), bboxSR=4326, imageSR=4326,
                      size="2048,1536", format="jpg", adjustAspectRatio="false",
                      mosaicRule=json.dumps(mosaic), renderingRule=json.dumps({"rasterFunction":"NaturalColor"}))
    requested_bounds = bounds
    extent = export["extent"]
    if extent.get("spatialReference", {}).get("wkid") != 4326:
        raise RuntimeError("USGS export is not geographic WGS84")
    bounds = [extent[k] for k in ("xmin","ymin","xmax","ymax")]
    if any(abs(actual-requested) > .000001 for actual,requested in zip(bounds, requested_bounds)):
        raise RuntimeError("Export coverage differs from the requested bounded area")
    href = export["href"]
    parsed = urllib.parse.urlsplit(href)
    if parsed.scheme != "https" or parsed.hostname != "imagery.nationalmap.gov":
        raise RuntimeError("USGS export returned an unexpected download host")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="detroit-imagery-", dir=destination.parent) as temporary:
        root = Path(temporary)
        with urllib.request.urlopen(href, timeout=90) as response:
            image = response.read(MAX_BYTES+1)
        if len(image) > MAX_BYTES or not image.startswith(b"\xff\xd8"):
            raise RuntimeError("USGS export is oversized or not a JPEG image")
        (root / "imagery.jpg").write_bytes(image)
        manifest = {"schema":1, "image":"imagery.jpg", "sha256":hashlib.sha256(image).hexdigest(),
                    "title":f"Detroit NAIP {year}", "attribution":f"USGS / USDA NAIP {year} · The National Map",
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
    parser.add_argument("--output", type=Path, default=detroit_pack_directory())
    args = parser.parse_args()
    try:
        download(args.output)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        parser.exit(1, f"Detroit imagery download: {error}\n")


if __name__ == "__main__":
    main()
