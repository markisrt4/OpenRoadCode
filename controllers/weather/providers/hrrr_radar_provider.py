# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Discover composite-reflectivity fields in NOAA's public HRRR GRIB2 archive."""

from datetime import datetime, timezone
from time import time
from urllib.parse import quote

import requests

from controllers.weather.radar_provider_if import RadarFrame, RadarProviderIf
from controllers.weather.hrrr_tiles import check_gdal_tools


def reflectivity_range(index: str, run: str):
    """Find the REFC entire-atmosphere message and its inclusive byte range."""
    records = []
    for line in index.splitlines():
        parts = line.split(":")
        if len(parts) >= 6:
            try:
                offset = int(parts[1])
            except ValueError:
                continue
            records.append((offset, parts))
    if any(offset < 0 for offset, _ in records) or any(
            records[i][0] >= records[i + 1][0] for i in range(len(records) - 1)):
        raise ValueError("NOAA HRRR index contains invalid byte offsets")
    matches = [i for i, (_, parts) in enumerate(records)
               if parts[2] == f"d={run}" and parts[3] == "REFC"
               and parts[4].startswith("entire atmosphere")]
    if len(matches) != 1:
        raise ValueError("NOAA HRRR index does not identify one composite-reflectivity field")
    i = matches[0]
    return records[i][0], records[i + 1][0] - 1 if i + 1 < len(records) else None


class HrrrRadarProvider(RadarProviderIf):
    """Select a complete HRRR run with six upcoming hourly CONUS forecasts."""

    ARCHIVE = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com"

    def __init__(self, *, session=None, timeout_seconds=20.0, clock=time):
        self._session = session or requests.Session()
        self._timeout = timeout_seconds
        self._clock = clock

    @property
    def provider_id(self):
        return "hrrr"

    def get_frames(self):
        check_gdal_tools()
        now = int(self._clock())
        current_hour = now // 3600 * 3600
        # Fall back as a whole rather than mixing different model runs.
        for age in range(5):
            run_time = current_hour - age * 3600
            run_date = datetime.fromtimestamp(run_time, timezone.utc)
            run = run_date.strftime("%Y%m%d%H")
            frames = []
            for step in range(1, 7):
                valid = current_hour + step * 3600
                lead = (valid - run_time) // 3600
                url = (f"{self.ARCHIVE}/hrrr.{run_date:%Y%m%d}/conus/"
                       f"hrrr.t{run_date:%H}z.wrfsfcf{lead:02d}.grib2")
                response = self._session.get(url + ".idx", timeout=self._timeout)
                try:
                    if response.status_code == 404:
                        break
                    response.raise_for_status()
                    start, end = reflectivity_range(response.text, run)
                finally:
                    response.close()
                frames.append(RadarFrame(
                    timestamp=valid,
                    tile_url=(f"orc-hrrr://{run}/f{lead:02d}/{{z}}/{{x}}/{{y}}.tiff"
                              f"?url={quote(url, safe='')}&start={start}&end={'' if end is None else end}"),
                    max_zoom=9,
                ))
            if len(frames) == 6:
                return tuple(frames)
        raise RuntimeError("NOAA HRRR has no complete recent run for the next six forecast hours")
