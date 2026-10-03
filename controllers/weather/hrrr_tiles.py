# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Download one HRRR GRIB field, decode with GDAL, and render map tiles."""

from io import BytesIO
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Lock
from urllib.parse import parse_qs, urlparse

from PIL import Image


def check_gdal_tools():
    """Require native tools packaged by Termux, without Python GDAL bindings."""
    for tool in ("gdal_translate", "gdalwarp", "gdalinfo"):
        if shutil.which(tool) is None:
            raise RuntimeError("HRRR needs GDAL; in Termux run: pkg install -y gdal")
    result = subprocess.run(["gdalinfo", "--formats"], capture_output=True, text=True, timeout=20)
    if result.returncode or not re.search(r"^\s*GRIB\s", result.stdout, re.MULTILINE):
        raise RuntimeError("Installed GDAL does not provide the GRIB decoder required for HRRR")


def tile_bounds(z, x, y):
    """Return an XYZ tile's EPSG:3857 bounds."""
    if not (0 <= z <= 9 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise ValueError("invalid HRRR tile coordinates")
    extent = 20037508.342789244
    span = 2 * extent / 2**z
    left, top = -extent + x * span, extent - y * span
    return left, top - span, left + span, top


def location_tile(latitude, longitude, zoom=7):
    """Return the XYZ tile containing a geographic location."""
    if not (math.isfinite(latitude) and math.isfinite(longitude)
            and -85.05112878 <= latitude <= 85.05112878 and -180 <= longitude <= 180
            and 0 <= zoom <= 9):
        raise ValueError("invalid diagnostic location")
    count = 2**zoom
    x = min(count - 1, int((longitude + 180) / 360 * count))
    lat = math.radians(latitude)
    y = min(count - 1, max(0, int((1 - math.asinh(math.tan(lat)) / math.pi) / 2 * count)))
    return zoom, x, y


def reflectivity_summary(data):
    """Count covered and visible-reflectivity pixels without confusing missing data with clear weather."""
    with Image.open(BytesIO(data)) as image:
        if image.mode not in ("F", "I", "I;16", "I;16B", "I;16L"):
            raise ValueError("HRRR did not produce raw single-band reflectivity")
        covered, visible, maximum = 0, 0, None
        for value in image.get_flattened_data():
            if math.isfinite(value) and -100 <= value <= 95:
                covered += 1
                visible += value >= 5
                maximum = value if maximum is None else max(maximum, value)
        return {"total": image.width * image.height, "covered": covered,
                "visible": visible, "max_dbz": maximum}


class HrrrTileSource:
    """Cache decoded fields and serialize native work to limit phone memory use."""

    def __init__(self, cache_root, session, timeout=30):
        self._root = Path(cache_root)
        self._session = session
        self._timeout = timeout
        self._lock = Lock()
        self._checked = False

    @staticmethod
    def _run(arguments):
        try:
            result = subprocess.run(arguments, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("HRRR GDAL processing timed out") from error
        if result.returncode:
            raise RuntimeError(f"HRRR GDAL processing failed: {result.stderr[-1000:]}")
        return result.stdout

    def _download(self, url, start, end):
        response = self._session.get(url, headers={"Range": f"bytes={start}-{'' if end is None else end}"},
                                     timeout=self._timeout, stream=True)
        try:
            response.raise_for_status()
            if response.status_code != 206:
                raise RuntimeError("NOAA did not honor the field byte range; refusing a full HRRR download")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
            if not match or int(match[1]) != start or (end is not None and int(match[2]) != end):
                raise RuntimeError("NOAA returned a different HRRR byte range")
            chunks, size = [], 0
            for chunk in response.iter_content(128 * 1024):
                size += len(chunk)
                if size > 16 * 1024 * 1024:
                    raise RuntimeError("HRRR reflectivity field exceeds the 16 MB download limit")
                chunks.append(chunk)
            data = b"".join(chunks)
            if (len(data) < 20 or data[:4] != b"GRIB" or data[7] != 2 or
                    data[-4:] != b"7777" or int.from_bytes(data[8:16], "big") != len(data) or
                    len(data) != int(match[2]) - start + 1):
                raise RuntimeError("NOAA returned an incomplete or invalid GRIB2 reflectivity field")
            return data
        finally:
            response.close()

    def tile(self, template, z, x, y):
        """Return a numeric TIFF tile in Web Mercator for subsequent coloring."""
        bounds = tile_bounds(z, x, y)
        parsed = urlparse(template)
        params = parse_qs(parsed.query, keep_blank_values=True)
        url = params.get("url", [""])[0]
        lead = parsed.path.strip("/").split("/")[0]
        if (not re.fullmatch(r"\d{10}", parsed.netloc) or not re.fullmatch(r"f\d{2}", lead)
                or not url.startswith("https://noaa-hrrr-bdp-pds.s3.amazonaws.com/hrrr.")):
            raise ValueError("invalid HRRR forecast field URL")
        element = params.get("element", ["REFC"])[0]
        fields = {"REFC": ("reflectivity", "0-EATM"), "TMP": ("temperature", "2-HTGL"),
                  "UGRD": ("wind-u", "10-HTGL"), "VGRD": ("wind-v", "10-HTGL")}
        if element not in fields:
            raise ValueError("unsupported HRRR field")
        name, short_name = fields[element]
        start = int(params.get("start", ["-1"])[0])
        end_text = params.get("end", [""])[0]
        end = int(end_text) if end_text else None
        if start < 0 or (end is not None and end < start):
            raise ValueError("invalid HRRR reflectivity byte range")
        with self._lock:
            if not self._checked:
                check_gdal_tools()
                self._checked = True
            directory = self._root / parsed.netloc / lead
            directory.mkdir(parents=True, exist_ok=True)
            raster = directory / f"{name}.tif"
            if not raster.is_file():
                field = directory / f"{name}.grib2"
                if not field.is_file():
                    temporary = field.with_suffix(".tmp")
                    temporary.write_bytes(self._download(url, start, end))
                    temporary.replace(field)
                metadata = json.loads(self._run(["gdalinfo", "--config", "GRIB_NORMALIZE_UNITS", "YES", "-json", str(field)]))
                bands = metadata.get("bands", [])
                attributes = bands[0].get("metadata", {}).get("", {}) if len(bands) == 1 else {}
                run_time = int(datetime.strptime(parsed.netloc, "%Y%m%d%H").replace(tzinfo=timezone.utc).timestamp())
                expected_time = run_time + int(lead[1:]) * 3600
                if (attributes.get("GRIB_ELEMENT") != element or
                        attributes.get("GRIB_SHORT_NAME") != short_name or
                        int(attributes.get("GRIB_VALID_TIME", "-1")) != expected_time):
                    detail = ("not composite reflectivity" if element == "REFC" else "the wrong variable or level")
                    raise RuntimeError(f"Downloaded HRRR field is {detail} at the requested forecast time")
                if element == "TMP" and attributes.get("GRIB_UNIT") not in {"[C]", "C"}:
                    raise RuntimeError("HRRR temperature was not decoded in Celsius")
                if element in {"UGRD", "VGRD"} and attributes.get("GRIB_UNIT") not in {"[m/s]", "m/s"}:
                    raise RuntimeError("HRRR wind was not decoded in meters per second")
                temporary = raster.with_suffix(".tmp.tif")
                self._run(["gdal_translate", "-q", "--config", "GDAL_CACHEMAX", "64",
                           "--config", "GRIB_NORMALIZE_UNITS", "YES",
                           "-of", "GTiff", "-ot", "Float32", "-b", "1",
                           "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", str(field), str(temporary)])
                temporary.replace(raster)
                # Retain two model runs; native work and pruning share the lock.
                runs = sorted(path for path in self._root.iterdir()
                              if path.is_dir() and re.fullmatch(r"\d{10}", path.name))
                for old in runs[:-2]:
                    if old.name != parsed.netloc:
                        shutil.rmtree(old)
            with TemporaryDirectory(prefix="tile-", dir=directory) as work:
                output = Path(work) / "tile.tif"
                self._run(["gdalwarp", "-q", "--config", "GDAL_CACHEMAX", "64",
                           "-wm", "64", "-t_srs", "EPSG:3857", "-te", *map(str, bounds),
                           "-ts", "256", "256", "-r", "near", "-ot", "Float32",
                           "-dstnodata", "-9999", "-of", "GTiff", str(raster), str(output)])
                return output.read_bytes()


def color_hrrr_reflectivity(data, color_table):
    """Convert raw numeric reflectivity into a transparent Universal PNG."""
    with Image.open(BytesIO(data)) as image:
        if image.mode not in ("F", "I", "I;16", "I;16B", "I;16L"):
            raise ValueError("HRRR did not produce raw single-band reflectivity")
        if image.size != (256, 256):
            raise ValueError("HRRR produced an unexpected tile size")
        colors = []
        for value in image.get_flattened_data():
            if not math.isfinite(value) or value < 5 or value > 95:
                colors.append((0, 0, 0, 0))
            else:
                _, rgb = min(color_table, key=lambda item: abs(item[0] - value))
                colors.append((*rgb, 255))
        result = Image.new("RGBA", image.size)
        result.putdata(colors)
        output = BytesIO()
        result.save(output, format="PNG")
        return output.getvalue()
