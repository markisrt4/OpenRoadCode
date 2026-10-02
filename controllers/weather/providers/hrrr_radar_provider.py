# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Discover NOAA HRRR forecast reflectivity frames from an ArcGIS image service."""

from datetime import datetime, timezone
import re
from time import time
from urllib.parse import quote

import requests

from controllers.weather.radar_provider_if import RadarFrame, RadarProviderIf


class HrrrRadarProvider(RadarProviderIf):
    """Expose the next six hours of CONUS simulated composite reflectivity."""

    DIRECTORY = "https://mapservices.weather.noaa.gov/raster/rest/services"

    def __init__(self, *, session=None, timeout_seconds=20.0, image_service=None, clock=time):
        self._session = session or requests.Session()
        self._timeout = timeout_seconds
        self._service = image_service
        self._clock = clock

    @property
    def provider_id(self):
        return "hrrr"

    def _json(self, url, **params):
        response = self._session.get(url, params={"f": "json", **params}, timeout=self._timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or "error" in payload:
            raise RuntimeError(f"NOAA HRRR service error: {payload.get('error') if isinstance(payload, dict) else payload}")
        return payload

    def get_frames(self):
        if self._service is None:
            services = self.list_services()
            matches = [item for item in services
                       if item.get("type") == "ImageServer"
                       and all(word in item.get("name", "").lower()
                               for word in ("hrrr", "composite", "reflectivity"))]
            if len(matches) != 1:
                available = [item.get("name") for item in services
                             if "hrrr" in item.get("name", "").lower()]
                raise RuntimeError(
                    "NOAA catalog does not identify one HRRR composite-reflectivity ImageServer. "
                    f"HRRR candidates: {available or 'none'}. Run the probe with --list-services."
                )
            self._service = f"{self.DIRECTORY}/{matches[0]['name']}/ImageServer"
        metadata = self._json(self._service)
        time_field = metadata.get("timeInfo", {}).get("startTimeField")
        id_field = metadata.get("objectIdField", "OBJECTID")
        if not all(isinstance(field, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field)
                   for field in (time_field, id_field)):
            raise RuntimeError("NOAA HRRR service does not expose a supported forecast time field")
        now = int(self._clock())
        end = now + 6 * 3600
        def sql_date(timestamp):
            return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        result = self._json(
            f"{self._service}/query",
            where=f"{time_field} > TIMESTAMP '{sql_date(now)}' AND {time_field} <= TIMESTAMP '{sql_date(end)}'",
            outFields=f"{id_field},{time_field}", returnGeometry="false",
            orderByFields=f"{time_field} ASC,{id_field} DESC", resultRecordCount=1000,
        )
        if result.get("exceededTransferLimit"):
            raise RuntimeError("NOAA HRRR query exceeded its record limit")
        by_time = {}
        for feature in result.get("features", []):
            attributes = feature.get("attributes", {})
            valid = attributes.get(time_field)
            raster_id = attributes.get(id_field)
            if not isinstance(valid, (int, float)) or not isinstance(raster_id, int):
                continue
            timestamp = int(valid / 1000)
            if now < timestamp <= end:
                by_time[timestamp] = max(raster_id, by_time.get(timestamp, -1))
        if not by_time:
            raise RuntimeError("NOAA HRRR has no upcoming forecast frames")
        return tuple(RadarFrame(
            timestamp=timestamp,
            tile_url=(f"orc-hrrr://{raster_id}/{{z}}/{{x}}/{{y}}.tiff"
                      f"?service={quote(self._service, safe='')}&refresh={now // 3600}"),
            max_zoom=9,
        ) for timestamp, raster_id in sorted(by_time.items()))

    def list_services(self):
        """Read only folders published by NOAA rather than assuming their names."""
        pending = [""]
        visited = set()
        services = []
        while pending:
            folder = pending.pop(0)
            if folder in visited:
                continue
            visited.add(folder)
            url = self.DIRECTORY + ("/" + quote(folder, safe="/") if folder else "")
            catalog = self._json(url)
            services.extend(item for item in catalog.get("services", []) if isinstance(item, dict))
            for child in catalog.get("folders", []):
                if isinstance(child, str) and child not in {"System", "Utilities"}:
                    pending.append(f"{folder}/{child}" if folder and not child.startswith(folder + "/") else child)
        return tuple(services)
