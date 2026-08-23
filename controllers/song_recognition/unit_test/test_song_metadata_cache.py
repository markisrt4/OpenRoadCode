# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.song_recognition.song_metadata_cache import SongMetadataCache
from controllers.song_recognition.song_recognition_if import SongRecognitionResult


class _Cache:
    def __init__(self):self.values={}
    def get(self,key):return self.values.get(key)
    def put(self,key,data):self.values[key]=data


def test_reuses_enriched_metadata_by_isrc() -> None:
    cache=SongMetadataCache(_Cache())
    enriched=SongRecognitionResult(title="Tom Sawyer",isrc="USMR18180103",artwork_url="https://images.test/tom-sawyer.jpg")
    cache.put_result_ids(enriched)
    fresh=SongRecognitionResult(title="Tom Sawyer",isrc="USMR18180103")
    assert cache.get_result(fresh) == enriched
