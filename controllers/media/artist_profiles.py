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
        key = "wikimedia-artist-v3:" + artist.strip().casefold()
        cached = self._cache.get(key)
        if cached:
            try:
                entry = json.loads(cached)
                if time() - entry["saved"] < _TTL:
                    cached_profile = entry["profile"]
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
        page = self._query(
            titles=artist,
            prop="extracts|pageimages|pageprops|info",
            exintro="1",
            explaintext="1",
            exchars="850",
            inprop="url",
            piprop="thumbnail|name",
            pilicense="free",
            pithumbsize="320",
        )["query"]["pages"][0]
        bio = page.get("extract", "").strip()
        if page.get("title", "").casefold() != artist.casefold() or not bio:
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
        thumbnail = page.get("thumbnail", {}).get("source", "")
        filename = page.get("pageimage")
        try:
            if not filename:
                entity = page.get("pageprops", {}).get("wikibase_item", "")
                if not re.fullmatch(r"Q[0-9]+", entity):
                    return None, "", ""
                url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity}.json"
                data = json.loads(self._fetch(url, 768_000))
                claim = data["entities"][entity]["claims"]["P18"][0]
                filename = claim["mainsnak"]["datavalue"]["value"]
            parameters = {
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "iiurlwidth": "320",
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
            thumbnail = file.get("thumburl") or thumbnail
            url = urlsplit(thumbnail)
            if url.scheme != "https" or url.hostname != "upload.wikimedia.org":
                return None, "", ""
            return self._fetch(thumbnail, 512_000), f"{credit} · {license_name}", str(source)
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            return None, "", ""
