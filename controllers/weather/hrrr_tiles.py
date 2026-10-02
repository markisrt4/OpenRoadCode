# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Request raw HRRR reflectivity in a map tile and color numeric dBZ values."""

from io import BytesIO
import json
import math
from urllib.parse import parse_qs, urlencode, urlparse

from PIL import Image


def hrrr_export_url(template, z, x, y):
    """Request one Web Mercator tile, locked to its forecast raster."""
    if not (0 <= z <= 9 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise ValueError("invalid HRRR tile coordinates")
    parsed = urlparse(template)
    raster_id = int(parsed.netloc)
    service = parse_qs(parsed.query).get("service", [""])[0]
    if not service.startswith("https://") or not service.endswith("/ImageServer"):
        raise ValueError("invalid HRRR image service")
    extent = 20037508.342789244
    span = 2 * extent / 2**z
    left, top = -extent + x * span, extent - y * span
    params = {
        "f": "image", "format": "tiff", "size": "256,256",
        "bbox": f"{left},{top-span},{left+span},{top}",
        "bboxSR": "3857", "imageSR": "3857",
        "interpolation": "RSP_NearestNeighbor",
        "renderingRule": json.dumps({"rasterFunction": "None"}),
        "mosaicRule": json.dumps({"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [raster_id]}),
    }
    return service + "/exportImage?" + urlencode(params)


def color_hrrr_reflectivity(data, color_table):
    """Convert raw numeric reflectivity into a transparent Universal PNG."""
    with Image.open(BytesIO(data)) as image:
        if image.mode not in ("F", "I", "I;16", "I;16B", "I;16L"):
            raise ValueError("NOAA HRRR did not return raw single-band reflectivity")
        if image.size != (256, 256):
            raise ValueError("NOAA HRRR returned an unexpected tile size")
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
