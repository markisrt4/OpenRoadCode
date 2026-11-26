"""Artist profiles persist through ORC's cache and skip ambiguous pages."""

import json
from unittest.mock import Mock

from controllers.cache.persistent_cache import PersistentCache
from controllers.media.artist_profiles import ArtistProfiles


def test_profile_is_reused_by_another_controller(tmp_path):
    response = {
        "query": {
            "pages": [
                {
                    "title": "Burl Ives",
                    "extract": "Burl Ives was an American singer and actor.",
                    "fullurl": "https://en.wikipedia.org/wiki/Burl_Ives",
                }
            ]
        }
    }
    fetch = Mock(return_value=json.dumps(response).encode())
    first = ArtistProfiles(PersistentCache(tmp_path), fetch).get("Burl Ives")
    again = ArtistProfiles(PersistentCache(tmp_path), fetch).get("Burl Ives")

    assert first is not None
    assert again == first
    fetch.assert_called_once()


def test_portrait_and_commons_credit_are_cached_with_profile(tmp_path):
    thumbnail = "https://upload.wikimedia.org/test.jpg"
    page = {
        "title": "Burl Ives",
        "extract": "Burl Ives was an American singer.",
        "fullurl": "https://en.wikipedia.org/wiki/Burl_Ives",
        "pageimage": "Burl Ives.jpg",
        "thumbnail": {"source": thumbnail},
    }
    image = {
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Burl_Ives.jpg",
        "extmetadata": {
            "Artist": {"value": "<em>Photographer</em>"},
            "LicenseShortName": {"value": "Public domain"},
        },
    }

    def response(item):
        return json.dumps({"query": {"pages": [item]}}).encode()

    fetch = Mock(side_effect=[response(page), response({"imageinfo": [image]}), b"portrait"])
    cache = PersistentCache(tmp_path)

    profile = ArtistProfiles(cache, fetch).get("Burl Ives")

    assert profile is not None
    assert profile.portrait == b"portrait"
    assert profile.portrait_credit == "Photographer · Public domain"
    assert fetch.call_args_list[1].args[0].startswith("https://commons.wikimedia.org/")
    assert ArtistProfiles(cache, fetch).get("Burl Ives") == profile
    assert fetch.call_count == 3


def test_uses_wikidata_image_when_article_has_no_thumbnail(tmp_path):
    page = {
        "title": "Burl Ives",
        "extract": "Burl Ives was an American singer.",
        "fullurl": "https://en.wikipedia.org/wiki/Burl_Ives",
        "pageprops": {"wikibase_item": "Q123"},
    }
    claim = {"mainsnak": {"datavalue": {"value": "Burl Ives.jpg"}}}
    image = {
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Burl_Ives.jpg",
        "thumburl": "https://upload.wikimedia.org/portrait.jpg",
        "extmetadata": {
            "Artist": {"value": "Photographer"},
            "LicenseShortName": {"value": "Public domain"},
        },
    }
    fetch = Mock(
        side_effect=[
            json.dumps({"query": {"pages": [page]}}).encode(),
            json.dumps({"entities": {"Q123": {"claims": {"P18": [claim]}}}}).encode(),
            json.dumps({"query": {"pages": [{"imageinfo": [image]}]}}).encode(),
            b"portrait",
        ]
    )

    profile = ArtistProfiles(PersistentCache(tmp_path), fetch).get("Burl Ives")

    assert profile is not None
    assert profile.portrait == b"portrait"
    assert fetch.call_args_list[1].args[0].endswith("/Q123.json")


def test_failed_article_portrait_uses_credited_wikidata_photo(tmp_path):
    page = {
        "title": "Burl Ives",
        "extract": "Burl Ives was an American singer.",
        "fullurl": "https://en.wikipedia.org/wiki/Burl_Ives",
        "pageimage": "Article.jpg",
        "pageprops": {"wikibase_item": "Q123"},
    }
    claim = {"mainsnak": {"datavalue": {"value": "Backup.jpg"}}}
    image = {
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Backup.jpg",
        "thumburl": "https://upload.wikimedia.org/backup.jpg",
        "extmetadata": {
            "Artist": {"value": "Photographer"},
            "LicenseShortName": {"value": "Public domain"},
        },
    }
    fetch = Mock(
        side_effect=[
            json.dumps({"query": {"pages": [page]}}).encode(),
            OSError("metadata temporarily unavailable"),
            json.dumps({"entities": {"Q123": {"claims": {"P18": [claim]}}}}).encode(),
            json.dumps({"query": {"pages": [{"imageinfo": [image]}]}}).encode(),
            b"backup",
        ]
    )

    profile = ArtistProfiles(PersistentCache(tmp_path), fetch).get("Burl Ives")

    assert profile is not None
    assert profile.portrait == b"backup"
    assert profile.portrait_credit == "Photographer · Public domain"


def test_profile_without_portrait_is_retried_after_one_hour(monkeypatch, tmp_path):
    page = {
        "title": "Burl Ives",
        "extract": "Burl Ives was an American singer.",
        "fullurl": "https://en.wikipedia.org/wiki/Burl_Ives",
    }
    clock = Mock(return_value=0)
    monkeypatch.setattr("controllers.media.artist_profiles.time", clock)
    fetch = Mock(return_value=json.dumps({"query": {"pages": [page]}}).encode())
    profiles = ArtistProfiles(PersistentCache(tmp_path), fetch)

    profiles.get("Burl Ives")
    clock.return_value = 3599
    profiles.get("Burl Ives")
    fetch.assert_called_once()
    clock.return_value = 3600
    profiles.get("Burl Ives")
    assert fetch.call_count == 2
