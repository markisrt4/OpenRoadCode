# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from controllers.radio.streaming_radio_directory_if import StreamingRadioDirectoryIf
from controllers.radio.streaming_radio_types import StreamingRadioStation


class RadioBrowserDirectory(StreamingRadioDirectoryIf):
    """Discover streaming stations through the Radio Browser JSON API."""

    DEFAULT_API_BASE = "https://de1.api.radio-browser.info/json"
    USER_AGENT = "OpenRoadCode/streaming-radio"

    def __init__(self, *, api_base: str = DEFAULT_API_BASE, timeout_s: float = 5.0) -> None:
        self._api_base = api_base.rstrip("/")
        self._timeout_s = timeout_s

    def search(self, query: str, *, limit: int = 20) -> tuple[StreamingRadioStation, ...]:
        query = query.strip()
        if not query:
            return ()
        return self._request_stations(
            {
                "name": query,
                "nameExact": "false",
                "hidebroken": "true",
                "order": "votes",
                "reverse": "true",
                "limit": str(_validate_limit(limit)),
            }
        )

    def stations_by_region(
        self,
        *,
        state: str,
        country_code: str = "US",
        limit: int = 50,
    ) -> tuple[StreamingRadioStation, ...]:
        state = state.strip()
        country_code = country_code.strip().upper()
        if not state:
            raise ValueError("state must not be empty")
        if len(country_code) != 2:
            raise ValueError("country_code must be a two-letter code")

        return self._request_stations(
            {
                "state": state,
                "countrycode": country_code,
                "hidebroken": "true",
                "order": "votes",
                "reverse": "true",
                "limit": str(_validate_limit(limit)),
            }
        )

    def _request_stations(self, params: dict[str, str]) -> tuple[StreamingRadioStation, ...]:
        url = f"{self._api_base}/stations/search?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": self.USER_AGENT})
        with urlopen(request, timeout=self._timeout_s) as response:
            payload = json.load(response)
        if not isinstance(payload, list):
            raise ValueError("Radio Browser returned an unexpected response")
        return tuple(station for item in payload if (station := _parse_station(item)) is not None)


def _parse_station(item: Any) -> StreamingRadioStation | None:
    if not isinstance(item, dict):
        return None

    station_id = str(item.get("stationuuid") or "").strip()
    name = str(item.get("name") or "").strip()
    stream_url = str(item.get("url_resolved") or item.get("url") or "").strip()
    if not station_id or not name or not stream_url:
        return None

    bitrate = item.get("bitrate")
    try:
        bitrate_kbps = int(bitrate) if bitrate not in (None, "") else None
    except (TypeError, ValueError):
        bitrate_kbps = None

    raw_tags = str(item.get("tags") or "")
    tags = tuple(tag.strip() for tag in raw_tags.split(",") if tag.strip())

    return StreamingRadioStation(
        station_id=station_id,
        name=name,
        stream_url=stream_url,
        homepage_url=_optional_text(item.get("homepage")),
        artwork_url=_optional_text(item.get("favicon")),
        state=_optional_text(item.get("state")),
        country_code=_optional_text(item.get("countrycode")),
        codec=_optional_text(item.get("codec")),
        bitrate_kbps=bitrate_kbps,
        tags=tags,
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    return min(limit, 500)
