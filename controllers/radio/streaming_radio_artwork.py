# SPDX-License-Identifier: MIT

"""Bounded artwork transport; image decoding and toolkit objects belong to views."""

from urllib.request import Request, urlopen

ARTWORK_LIMIT_BYTES = 2 * 1024 * 1024


def download_station_artwork(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "OpenRoadCode/streaming-radio"})
    with urlopen(request, timeout=5.0) as response:
        payload = bytes(response.read(ARTWORK_LIMIT_BYTES + 1))
    if len(payload) > ARTWORK_LIMIT_BYTES:
        raise ValueError("station artwork exceeds 2 MiB")
    return payload
