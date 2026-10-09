"""Download a coarse 33x33 USGS 3DEP ground grid; preserve raw source responses."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.parse
import urllib.request

from apps.launchers.local_terrain_pack import detroit_terrain_directory, load_terrain

SERVICE = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer"
BOUNDS = (-83.065, 42.315, -83.025, 42.345)
SIZE = 33


def request(endpoint, parameters):
    payload = urllib.parse.urlencode({"f":"json", **parameters}).encode()
    url = SERVICE+endpoint if endpoint else SERVICE+"?"+payload.decode()
    with urllib.request.urlopen(url, data=payload if endpoint else None, timeout=90) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError(f"USGS elevation error: {result['error']}")
    return result


def download(destination):
    if destination.exists():
        state = load_terrain(destination)
        print(f"Terrain already installed: {destination} ({state.width}x{state.height})")
        return
    metadata = request("", {})
    if metadata.get("pixelType") != "F32" or metadata.get("serviceDataType") != "esriImageServiceDataTypeElevation":
        raise RuntimeError("Expected raw USGS elevation service; source review required")
    west,south,east,north = BOUNDS
    points = [[west+(east-west)*col/(SIZE-1), north-(north-south)*row/(SIZE-1)]
              for row in range(SIZE) for col in range(SIZE)]
    values, responses = {}, []
    for start in range(0,len(points),128):
        group = points[start:start+128]
        reply = request("/getSamples", {
            "geometry":json.dumps({"points":group,"spatialReference":{"wkid":4326}}),
            "geometryType":"esriGeometryMultipoint", "returnFirstValueOnly":"true",
            "interpolation":"RSP_BilinearInterpolation",
            "renderingRule":json.dumps({"rasterFunction":"None"}),
            "outFields":"Name,ProductName,VerticalDatum,Source,AcquisitionDate",
        })
        responses.append(reply)
        expected = {(round(x,7),round(y,7)) for x,y in group}
        for sample in reply.get("samples", []):
            location = sample["location"]
            key = (round(location["x"],7),round(location["y"],7))
            if key not in expected:
                raise RuntimeError("USGS returned unexpected sample coordinates")
            value = float(sample["value"])
            if not math.isfinite(value) or not -500 <= value <= 9000:
                raise RuntimeError("USGS returned no-data or invalid elevation")
            if key in values:
                raise RuntimeError("USGS returned duplicate ground samples")
            values[key] = value
        print(f"Sampled {min(start+128,len(points))}/{len(points)} ground points")
    if len(values) != len(points):
        raise RuntimeError("USGS did not return every ground point; incomplete pack not installed")
    heights = [values[(round(x,7),round(y,7))] for x,y in points]
    datums = sorted({str(sample.get("attributes",{}).get("VerticalDatum"))
                    for reply in responses for sample in reply.get("samples",[])
                    if sample.get("attributes",{}).get("VerticalDatum")})
    if len(datums) > 1:
        raise RuntimeError("USGS returned mixed source datums; datum review required")
    datum = "; ".join(datums) or "USGS 3DEP source datum; not converted to ellipsoid heights"
    data = {"width":SIZE,"height":SIZE,"heights_m":heights,
            "reference_height_m":heights[len(heights)//2],"vertical_datum":datum}
    content = json.dumps(data).encode()
    manifest = {"schema":1,"title":"Detroit 3DEP relative relief","attribution":"USGS 3DEP · The National Map",
                "bounds_deg":BOUNDS,"sha256":hashlib.sha256(content).hexdigest(),"source":SERVICE,
                "rights":"Public-domain USGS 3DEP elevation", "rights_reference":"https://www.usgs.gov/3d-elevation-program/about-3dep-products-services",
                "downloaded_at":datetime.now(timezone.utc).isoformat(), "sampling":"33x33 bilinear samples, about 100 metres apart"}
    destination.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix="detroit-terrain-",dir=destination.parent) as temporary:
        root = Path(temporary)
        (root/"terrain.json").write_bytes(content)
        (root/"manifest.json").write_text(json.dumps(manifest,indent=2))
        (root/"source-service.json").write_text(json.dumps(metadata,indent=2))
        (root/"source-samples.json").write_text(json.dumps(responses))
        load_terrain(root)
        root.rename(destination)
    print(f"Installed {len(content):,} terrain bytes at {destination}")
    print(f"Source elevations: {min(heights):.1f}–{max(heights):.1f} m; scene uses relative relief, not converted absolute elevations")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=detroit_terrain_directory())
    args = parser.parse_args()
    try:
        download(args.output)
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as error:
        parser.exit(1,f"Detroit terrain download: {error}\n")


if __name__ == "__main__":
    main()
