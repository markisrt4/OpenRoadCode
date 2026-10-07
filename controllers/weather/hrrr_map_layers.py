# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Discover and color full-area HRRR temperature and wind-speed fields."""

from datetime import datetime, timezone
from io import BytesIO
import math
from time import time
from urllib.parse import quote

from PIL import Image
import requests

from controllers.weather.hrrr_tiles import check_gdal_tools
from controllers.weather.providers.hrrr_radar_provider import HrrrRadarProvider
from controllers.weather.radar_provider_if import RadarFrame


TEMPERATURE_COLORS = ((-30, (98, 61, 166)), (-10, (47, 102, 190)), (0, (71, 187, 226)),
                      (10, (87, 194, 128)), (20, (242, 219, 82)), (30, (243, 140, 53)),
                      (40, (205, 58, 67)))
WIND_COLORS = ((0, (62, 151, 187)), (5, (94, 194, 146)), (10, (241, 221, 89)),
               (15, (244, 145, 64)), (25, (209, 62, 98)), (40, (146, 76, 192)))


def field_range(index, run, element, level):
    """Find exactly one selected HRRR field and its bounded GRIB message range."""
    records = []
    for line in index.splitlines():
        parts = line.split(":")
        if len(parts) >= 6:
            try:
                records.append((int(parts[1]), parts))
            except ValueError:
                continue
    if any(offset < 0 for offset, _ in records) or any(a[0] >= b[0] for a, b in zip(records, records[1:])):
        raise ValueError("HRRR index contains invalid byte offsets")
    matches = [i for i, (_, parts) in enumerate(records)
               if parts[2] == f"d={run}" and parts[3] == element and parts[4] == level]
    if len(matches) != 1:
        raise ValueError(f"HRRR index does not identify one {element} {level} field")
    i = matches[0]
    return records[i][0], records[i + 1][0] - 1 if i + 1 < len(records) else None


class HrrrMapLayerProvider:
    """Select the nearest future hour from a recent CONUS HRRR run."""

    def __init__(self, session=None, clock=time):
        self._session = session or requests.Session()
        self._clock = clock

    def close(self):
        """Release connections after pending work completes."""
        self._session.close()

    def get_frame(self, kind):
        if kind not in {"temperature", "wind"}:
            raise ValueError("Unsupported HRRR map layer")
        check_gdal_tools()
        hour = int(self._clock()) // 3600 * 3600
        valid = hour + 3600
        for age in range(5):
            run_time = hour - age * 3600
            date = datetime.fromtimestamp(run_time, timezone.utc)
            run = date.strftime("%Y%m%d%H")
            lead = (valid - run_time) // 3600
            url = f"{HrrrRadarProvider.ARCHIVE}/hrrr.{date:%Y%m%d}/conus/hrrr.t{date:%H}z.wrfsfcf{lead:02d}.grib2"
            response = self._session.get(url + ".idx", timeout=20)
            try:
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                index = response.text
            finally:
                response.close()

            def template(element, level):
                start, end = field_range(index, run, element, level)
                return (f"orc-hrrr-layer://{run}/f{lead:02d}/{{z}}/{{x}}/{{y}}.tiff"
                        f"?url={quote(url, safe='')}&start={start}&end={'' if end is None else end}&element={element}")

            if kind == "temperature":
                field = template("TMP", "2 m above ground")
            else:
                field = template("UGRD", "10 m above ground")
                secondary = template("VGRD", "10 m above ground")
                field += "&secondary=" + quote(secondary, safe="")
            return RadarFrame(valid, field + f"&kind={kind}", max_zoom=9)
        raise RuntimeError("NOAA HRRR has no recent forecast for this map layer")


def color_model_layer(data, kind, secondary=None):
    """Render a numeric field as a continuous temperature or wind-speed heatmap."""
    if kind not in {"temperature", "wind"}:
        raise ValueError("Unsupported model layer")

    def pixels(raw):
        with Image.open(BytesIO(raw)) as image:
            if image.mode not in ("F", "I", "I;16", "I;16B", "I;16L") or image.size != (256, 256):
                raise ValueError("HRRR layer did not produce a raw 256x256 numeric tile")
            return list(image.get_flattened_data())

    values = pixels(data)
    if kind == "wind":
        if secondary is None:
            raise ValueError("Wind speed needs both vector components")
        north = pixels(secondary)
        values = [math.hypot(u, v) if math.isfinite(u) and math.isfinite(v) and abs(u) <= 200 and abs(v) <= 200
                  else float("nan") for u, v in zip(values, north)]
    table = TEMPERATURE_COLORS if kind == "temperature" else WIND_COLORS
    colors = []
    for value in values:
        valid = math.isfinite(value) and (-100 <= value <= 70 if kind == "temperature" else 0 <= value <= 200)
        if not valid:
            colors.append((0, 0, 0, 0))
            continue
        lower, upper = table[0], table[-1]
        for a, b in zip(table, table[1:]):
            if value <= b[0]:
                lower, upper = a, b
                break
        fraction = max(0, min(1, (value - lower[0]) / (upper[0] - lower[0])))
        colors.append((*[round(a + fraction * (b - a)) for a, b in zip(lower[1], upper[1])], 255))
    image = Image.new("RGBA", (256, 256))
    image.putdata(colors)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
