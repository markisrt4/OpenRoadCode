# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.spotify.spotify_web_api_controller import SpotifyWebApiController


class _Client:
    def __init__(self):self.requests=[]
    def request(self,method,path,*,body=None):self.requests.append((method,path,body))
    def request_json(self,method,path,*,body=None):
        self.requests.append((method,path,body))
        return {"id":"track-1","uri":"spotify:track:track-1","external_urls":{"spotify":"https://open.spotify.test/track-1"},"album":{"images":[{"url":"https://images.test/cover.jpg"}]}}


def test_plays_one_track_uri() -> None:
    client=_Client();controller=SpotifyWebApiController(client)
    controller.play_uri("spotify:track:track-1")
    assert client.requests == [("PUT","/me/player/play",{"uris":["spotify:track:track-1"]})]


def test_loads_track_artwork_metadata() -> None:
    client=_Client();controller=SpotifyWebApiController(client)
    metadata=controller.track_metadata("track-1")
    assert metadata is not None
    assert metadata.artwork_url == "https://images.test/cover.jpg"
    assert metadata.uri == "spotify:track:track-1"
