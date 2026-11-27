"""Load and cache exact-title Wikimedia artist profiles."""

import base64
import html
import json
import re
from collections.abc import Callable
from dataclasses import asdict
from time import time
from typing import Any, cast
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from controllers.cache.persistent_cache_if import PersistentCacheIf
from ui.media.artist_profile import ArtistProfile

_API = "https://en.wikipedia.org/w/api.php"
_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_TTL = 7 * 86400
_MISSING_PORTRAIT_TTL = 3600


def _download(url: str, limit: int) -> bytes:
    request = Request(
        url, headers={"User-Agent": "OpenRoadCode/1.0 (https://github.com/markisrt4/OpenRoadCode)"}
    )
    with urlopen(request, timeout=5) as response:
        data = response.read(limit + 1)
    if not isinstance(data, bytes):
        raise TypeError("Artist profile response must contain bytes")
    if len(data) > limit:
        raise ValueError("Artist profile response is too large")
    return data


class ArtistProfiles:
    """Resolve profiles using ORC's persistent cache and a bounded HTTP fetcher."""

    def __init__(
        self, cache: PersistentCacheIf, fetch: Callable[[str, int], bytes] = _download
    ) -> None:
        self._cache = cache
        self._fetch = fetch

    def get(self, artist: str) -> ArtistProfile | None:
        """Return an exact article match, using a cached profile when available."""
        key = "wikimedia-artist-v4:" + artist.strip().casefold()
        cached = self._cache.get(key)
        if cached:
            try:
                entry = json.loads(cached)
                cached_profile = entry["profile"]
                ttl = (
                    _TTL if cached_profile and cached_profile["portrait"] else _MISSING_PORTRAIT_TTL
                )
                if time() - entry["saved"] < ttl:
                    if cached_profile is None:
                        return None
                    if cached_profile["portrait"]:
                        cached_profile["portrait"] = base64.b64decode(
                            cached_profile["portrait"], validate=True
                        )
                    return ArtistProfile(**cached_profile)
            except (TypeError, KeyError, ValueError):
                pass
        profile: ArtistProfile | None = self._lookup(artist.strip())
        payload = asdict(profile) if profile else None
        if payload is not None and profile is not None and profile.portrait:
            payload["portrait"] = base64.b64encode(profile.portrait).decode("ascii")
        self._cache.put(key, json.dumps({"saved": time(), "profile": payload}).encode())
        return profile

    def _query(self, endpoint: str = _API, **params: str) -> dict[str, Any]:
        url = (
            endpoint
            + "?"
            + urlencode({"action": "query", "format": "json", "formatversion": "2", **params})
        )
        return cast(dict[str, Any], json.loads(self._fetch(url, 256_000)))

    def _lookup(self, artist: str) -> ArtistProfile | None:
        result = self._query(
            titles=artist,
            redirects="1",
            prop="extracts|pageimages|pageprops|info",
            exintro="1",
            explaintext="1",
            exchars="850",
            inprop="url",
            piprop="thumbnail|name",
            pilicense="free",
            pithumbsize="330",
        )["query"]
        page = result["pages"][0]
        bio = page.get("extract", "").strip()
        if not bio or (
            page.get("title", "").casefold() != artist.casefold()
            and not any(
                link["from"].casefold() == artist.casefold() for link in result.get("redirects", [])
            )
        ):
            return None
        if "disambiguation" in page.get("pageprops", {}):
            return None
        if not re.search(
            r"\b(singer|musician|band|vocalist|rapper|composer|songwriter|recording artist)\b",
            bio,
            re.I,
        ):
            return None
        image, credit, source = self._portrait(page)
        return ArtistProfile(artist, bio, page["fullurl"], image, credit, source)

    def _portrait(self, page: dict[str, Any]) -> tuple[bytes | None, str, str]:
        filename = page.get("pageimage")
        thumbnail = page.get("thumbnail", {}).get("source", "")
        if filename:
            portrait = self._file_portrait(filename, thumbnail)
            if portrait[0]:
                return portrait

        entity = page.get("pageprops", {}).get("wikibase_item", "")
        if not re.fullmatch(r"Q[0-9]+", entity):
            return None, "", ""
        try:
            url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity}.json"
            data = json.loads(self._fetch(url, 768_000))
            claim = data["entities"][entity]["claims"]["P18"][0]
            fallback = claim["mainsnak"]["datavalue"]["value"]
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            return None, "", ""
        return self._file_portrait(fallback)

    def _file_portrait(self, filename: str, thumbnail: str = "") -> tuple[bytes | None, str, str]:
        try:
            parameters = {
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "iiextmetadatafilter": "Artist|LicenseShortName",
                "iiurlwidth": "330",
            }
            info = self._query(_COMMONS_API, redirects="1", **parameters)
            if not info["query"]["pages"][0].get("imageinfo"):
                info = self._query(redirects="1", **parameters)
            file = info["query"]["pages"][0]["imageinfo"][0]
            meta = file["extmetadata"]
            credit = html.unescape(re.sub(r"<[^>]+>", "", meta["Artist"]["value"])).strip()
            license_name = meta["LicenseShortName"]["value"]
            source = file["descriptionurl"]
            if not credit or not license_name:
                return None, "", ""
            for candidate in dict.fromkeys((file.get("thumburl"), thumbnail, file.get("url"))):
                if not candidate:
                    continue
                parsed_candidate = urlsplit(candidate)
                if (
                    parsed_candidate.scheme != "https"
                    or parsed_candidate.hostname != "upload.wikimedia.org"
                ):
                    continue
                try:
                    image = self._fetch(candidate, 512_000)
                except (OSError, ValueError):
                    continue
                if image:
                    return image, f"{credit} · {license_name}", str(source)
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            pass
        return None, "", ""
