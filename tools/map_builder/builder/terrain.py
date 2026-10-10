"""Download a coarse 65x65 USGS 3DEP ground grid; preserve raw source responses."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .map_3d import PRESETS

SERVICE = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer"
EPQS = "https://epqs.nationalmap.gov/v1/json"


class ElevationServiceError(RuntimeError):
    def __init__(self, error):
        self.code = error.get('code')
        super().__init__(f"USGS elevation error: {error}")


def request(endpoint, parameters):
    payload = urllib.parse.urlencode({"f":"json", **parameters}).encode()
    url = SERVICE+endpoint if endpoint else SERVICE+"?"+payload.decode()
    return _json_request(url, payload if endpoint else None)


def _json_request(url, data=None):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent':'OpenRoadCode terrain installer'})
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.load(response)
            break
        except (URLError, TimeoutError) as error:
            if (isinstance(error, HTTPError) and error.code not in (429,500,502,503,504)) or attempt == 2:
                raise
            print(f"USGS request failed; retry {attempt+1}/2: {error}")
            time.sleep(attempt+1)
    if "error" in result:
        raise ElevationServiceError(result['error'])
    return result


def download(destination, preset, *, size=65):
    try:
        return _download_image_server(destination, preset, size=size)
    except (ElevationServiceError, URLError, TimeoutError) as error:
        if isinstance(error, ElevationServiceError) and error.code not in (498,499,429,500,502,503,504):
            raise
        if isinstance(error, HTTPError) and error.code not in (498,499,429,500,502,503,504):
            raise
        print(f'USGS image service unavailable ({error}); switching to public EPQS without credentials.')
        print('Fallback: 33×33 ground grid, two concurrent requests. This can take several minutes.')
        return _download_epqs(destination, preset, size=min(size,33))


def _download_image_server(destination, preset, *, size):
    if type(size) is not int or not 2 <= size <= 129:
        raise ValueError('Terrain grid size must be between 2 and 129')
    title, bounds = PRESETS[preset]
    if destination.exists():
        validate_terrain(destination)
        print(f"Terrain already installed: {destination}")
        return
    metadata = request("", {})
    if metadata.get("pixelType") != "F32" or metadata.get("serviceDataType") != "esriImageServiceDataTypeElevation":
        raise RuntimeError("Expected raw USGS elevation service; source review required")
    west,south,east,north = bounds
    points = [[west+(east-west)*col/(size-1), north-(north-south)*row/(size-1)]
              for row in range(size) for col in range(size)]
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
    _install_pack(destination,title,bounds,size,heights,datum,metadata,responses,SERVICE,'bilinear samples')


def _install_pack(destination,title,bounds,size,heights,datum,metadata,responses,source,sampling):
    data = {"width":size,"height":size,"heights_m":heights,
            "reference_height_m":heights[len(heights)//2],"vertical_datum":datum}
    content = json.dumps(data).encode()
    manifest = {"schema":1,"tiles":[],"layers":["terrain"],"title":title+" 3DEP terrain","attribution":"USGS 3DEP · The National Map",
                "bounds_deg":bounds,"sha256":hashlib.sha256(content).hexdigest(),"source":source,
                "rights":"Public-domain USGS 3DEP elevation", "rights_reference":"https://www.usgs.gov/3d-elevation-program/about-3dep-products-services",
                "downloaded_at":datetime.now(timezone.utc).isoformat(),
                "sampling":f"{size}x{size} {sampling}; north-to-south rows; elevations in metres"}
    destination.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix="detroit-terrain-",dir=destination.parent) as temporary:
        root = Path(temporary)
        (root/"terrain.json").write_bytes(content)
        (root/"manifest.json").write_text(json.dumps(manifest,indent=2))
        (root/"source-service.json").write_text(json.dumps(metadata,indent=2))
        (root/"source-samples.json").write_text(json.dumps(responses))
        validate_terrain(root)
        root.rename(destination)
    print(f"Installed {len(content):,} terrain bytes at {destination}")
    print(f"Source elevations: {min(heights):.1f}–{max(heights):.1f} m; scene uses relative relief, not converted absolute elevations")



def _epqs_point(x,y):
    reply = _json_request(EPQS+'?'+urllib.parse.urlencode(
        {'x':x,'y':y,'units':'Meters','includeDate':'false'}))
    location = reply.get('location', {})
    if (not math.isclose(float(location['x']),x,abs_tol=1e-7)
            or not math.isclose(float(location['y']),y,abs_tol=1e-7)):
        raise RuntimeError('EPQS returned unexpected sample coordinates')
    value = float(reply['value'])
    if not math.isfinite(value) or not -500 <= value <= 9000:
        raise RuntimeError('EPQS returned no-data or invalid elevation')
    return value,reply


def _download_epqs(destination,preset,*,size):
    title,bounds = PRESETS[preset]
    west,south,east,north = bounds
    points = [(west+(east-west)*col/(size-1),north-(north-south)*row/(size-1))
              for row in range(size) for col in range(size)]
    heights,responses = [None]*len(points),[None]*len(points)
    executor = ThreadPoolExecutor(max_workers=2)
    try:
        pending = {executor.submit(_epqs_point,x,y):index for index,(x,y) in enumerate(points)}
        for count,future in enumerate(as_completed(pending),1):
            index = pending[future]
            heights[index],responses[index] = future.result()
            if count % 32 == 0 or count == len(points):
                print(f'EPQS sampled {count}/{len(points)} ground points',flush=True)
    finally:
        executor.shutdown(wait=True,cancel_futures=True)
    datum = 'USGS EPQS source datum not specified; not converted to ellipsoid heights'
    _install_pack(destination,title,bounds,size,heights,datum,
                  {'source':EPQS,'units':'Meters','method':'Elevation Point Query Service'},
                  responses,EPQS,'EPQS point samples')


def validate_terrain(root):
    root = Path(root).resolve()
    manifest = json.loads((root/'manifest.json').read_text())
    if not manifest.get('attribution') or not manifest.get('source') or not manifest.get('rights_reference'):
        raise ValueError('Terrain requires attribution and source/rights metadata')
    payload = (root/'terrain.json').resolve()
    if not payload.is_relative_to(root) or payload.stat().st_size > 2*1024*1024:
        raise ValueError('Terrain payload outside pack or oversized')
    content = payload.read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest['sha256']:
        raise ValueError('Terrain checksum mismatch')
    data = json.loads(content)
    width, height = data['width'], data['height']
    if type(width) is not int or type(height) is not int or not 2 <= width <= 129 or not 2 <= height <= 129:
        raise ValueError('Invalid terrain dimensions')
    if len(data['heights_m']) != width*height or not all(
            type(v) in (int,float) and math.isfinite(v) and -500 <= v <= 9000 for v in data['heights_m']):
        raise ValueError('Invalid terrain samples')
    if not math.isfinite(data['reference_height_m']) or not data['vertical_datum'].strip():
        raise ValueError('Terrain requires a reference height and source datum')
    return data
