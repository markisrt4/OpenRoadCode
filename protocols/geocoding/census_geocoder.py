# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Bounded US Census address lookup without an API key or GUI dependency."""

import json
import math
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError


@dataclass(frozen=True)
class AddressMatch:
    address: str
    latitude_deg: float
    longitude_deg: float


class CensusGeocoder:
    ENDPOINT = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"

    def __init__(self, *, timeout=8.0, opener=urlopen):
        self._timeout, self._opener = timeout, opener

    def geocode(self, address: str) -> tuple[AddressMatch, ...]:
        query = urlencode({"address": address, "benchmark": "Public_AR_Current", "format": "json"})
        request = Request(self.ENDPOINT + "?" + query,
                          headers={"User-Agent": "OpenRoadCode/1.0 (+https://github.com/markisrt4/OpenRoadCode)",
                                   "Accept": "application/json"})
        try:
            with self._opener(request, timeout=self._timeout) as response:
                raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("Response too large")
            document = json.loads(raw)
            if not isinstance(document, dict) or not isinstance(document.get("result"), dict):
                raise ValueError("Invalid response")
            entries = document["result"].get("addressMatches", [])
            if not isinstance(entries, list):
                raise ValueError("Invalid address matches")
            matches = []
            for item in entries[:5]:
                coordinates = item["coordinates"]
                lat, lon = float(coordinates["y"]), float(coordinates["x"])
                if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                    continue
                matches.append(AddressMatch(str(item["matchedAddress"]), lat, lon))
            return tuple(matches)
        except (OSError, URLError, ValueError, KeyError, TypeError) as error:
            raise RuntimeError("Online address search unavailable. Check internet access and try again.") from error
