"""Explicit one-time OSM download; simple closed ways only, no hosted viewer layer."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import time
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.parse
import urllib.request

from apps.launchers.local_building_pack import detroit_building_directory, load_buildings
from ui.navigation.local_building_state import LocalBuilding, LocalBuildingState

SERVICE = "https://overpass-api.de/api/interpreter"
BOUNDS = (-83.065, 42.315, -83.025, 42.345)


def height(tags):
    for key, source, scale in (("height", "osm-height", 1), ("building:levels", "levels-estimate", 3)):
        try:
            raw = tags.get(key, "").strip()
            value = float(raw.removesuffix(" m")) * scale
            if math.isfinite(value) and 1 <= value <= 1000:
                return value, source
        except (ValueError, AttributeError):
            pass
    return 9.0, "placeholder"


def parse_buildings(reply, bounds=BOUNDS):
    if reply.get("remark"):
        raise RuntimeError("Overpass returned an incomplete/error response: "+reply["remark"])
    buildings, skipped = [], 0
    west, south, east, north = bounds
    for element in reply.get("elements", []):
        tags = element.get("tags", {})
        geometry = element.get("geometry", [])
        if (element.get("type") != "way" or tags.get("building") in (None, "no")
                or len(geometry) < 4 or geometry[0] != geometry[-1]
                or len(geometry) > 2000
                or any(not (west <= p["lon"] <= east and south <= p["lat"] <= north) for p in geometry)):
            skipped += 1
            continue
        ring = tuple((math.radians(p["lon"]), math.radians(p["lat"])) for p in geometry)
        buildings.append(LocalBuilding(ring, *height(tags)))
    return tuple(buildings), skipped


def prepare(reply):
    buildings, skipped = parse_buildings(reply)
    return LocalBuildingState(buildings), skipped


def request_tile(bounds):
    west, south, east, north = bounds
    query = f'[out:json][timeout:25];way["building"]({south},{west},{north},{east});out geom;'
    request = urllib.request.Request(SERVICE, data=urllib.parse.urlencode({"data":query}).encode(),
                                     headers={"User-Agent":"OpenRoadCode-Detroit-prototype/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read(20*1024*1024+1)
            if len(raw) > 20*1024*1024:
                raise ValueError("Source response exceeds 20 MB")
            reply = json.loads(raw)
            if reply.get("remark"):
                raise RuntimeError("Overpass incomplete response: "+reply["remark"])
            if not isinstance(reply.get("elements"), list):
                raise ValueError("Missing OSM elements")
            return raw
        except urllib.error.HTTPError as error:
            if error.code not in (429, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError, RuntimeError):
            if attempt == 2:
                raise
        delay = 2**(attempt+1)
        print(f"Service busy; retry {attempt+2}/3 in {delay}s", flush=True)
        time.sleep(delay)


def download(destination):
    if destination.exists():
        print(f"Buildings already installed: {len(load_buildings(destination).buildings)} outlines")
        return
    west, south, east, north = BOUNDS
    mid_lon, mid_lat = (west+east)/2, (south+north)/2
    tiles = [(w,s,e,n) for w,e in ((west,mid_lon),(mid_lon,east))
             for s,n in ((south,mid_lat),(mid_lat,north))]
    # Successful tiles survive a failed request or Ctrl+C; never install a partial pack.
    cache = destination.with_name(destination.name+".download")
    cache.mkdir(parents=True, exist_ok=True)
    elements, sources = {}, []
    for index, bounds in enumerate(tiles):
        path = cache/f"tile-{index}.json"
        print(f"Buildings tile {index+1}/{len(tiles)}"+(" (cached)" if path.exists() else ""), flush=True)
        if path.exists():
            raw = path.read_bytes()
        else:
            raw = request_tile(bounds)
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(raw)
            temporary.replace(path)
        reply = json.loads(raw)
        if reply.get("remark") or not isinstance(reply.get("elements"), list):
            raise ValueError(f"Invalid cached tile; remove {path} and retry")
        sources.append(raw)
        for element in reply["elements"]:
            elements[(element["type"],element["id"])] = element
    merged = {"elements":list(elements.values())}
    state, skipped = prepare(merged)
    raw = json.dumps(merged).encode()
    content = json.dumps(state.document()).encode()
    if len(content) > 10*1024*1024:
        raise ValueError("Prepared building pack exceeds 10 MB")
    manifest = {"schema":1, "sha256":hashlib.sha256(content).hexdigest(),
                "bounds_deg":BOUNDS, "source":SERVICE, "license":"ODbL-1.0",
                "license_url":"https://opendatacommons.org/licenses/odbl/1-0/",
                "attribution_url":"https://www.openstreetmap.org/copyright",
                "downloaded_utc":datetime.now(timezone.utc).isoformat(), "skipped":skipped}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent, prefix=".buildings-") as temporary:
        prepared = Path(temporary)/"pack"
        prepared.mkdir()
        (prepared/"buildings.json").write_bytes(content)
        (prepared/"source-osm.json").write_bytes(raw)
        for index, source in enumerate(sources):
            (prepared/f"source-tile-{index}.json").write_bytes(source)
        (prepared/"manifest.json").write_text(json.dumps(manifest, indent=2))
        load_buildings(prepared)
        prepared.rename(destination)
    print(f"Installed {len(state.buildings)} outlines ({len(content)/1024:.0f} KB); skipped {skipped}. Heights include estimates/placeholders.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=detroit_building_directory())
    args = parser.parse_args()
    try:
        download(args.destination)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        parser.exit(1, f"Building download: {error}\n")


if __name__ == "__main__":
    main()
