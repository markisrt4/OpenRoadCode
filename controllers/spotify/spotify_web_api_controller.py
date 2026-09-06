# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify application controller backed by the Spotify Web API."""

from __future__ import annotations
from typing import Any
from urllib.parse import quote, urlencode
from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_library import SpotifyLibraryTrack, SpotifyPlaylist
from controllers.spotify.spotify_state import SpotifyState
from protocols.spotify import SpotifyWebApiClient

class SpotifyWebApiController(SpotifyControllerIf):
    """Control Spotify playback and read user media through the Web API."""
    def __init__(self,client:SpotifyWebApiClient)->None:self._client=client; self._last_state=SpotifyState(is_available=False,status_message="Spotify not loaded")
    def current_state(self)->SpotifyState:
        try:
            response=self._client.request_json("GET","/me/player")
            if response is None:self._last_state=SpotifyState(is_available=False,status_message="No active Spotify playback"); return self._last_state
            self._last_state=self._create_state(response); return self._last_state
        except Exception as exc:self._last_state=SpotifyState(is_available=False,status_message=f"Spotify error: {exc}"); return self._last_state
    def play(self)->None:self._client.request("PUT","/me/player/play")
    def pause(self)->None:self._client.request("PUT","/me/player/pause")
    def play_pause(self)->None:self.pause() if self.current_state().is_playing else self.play()
    def next_track(self)->None:self._client.request("POST","/me/player/next")
    def previous_track(self)->None:self._client.request("POST","/me/player/previous")
    def set_volume_percent(self,volume_percent:int)->None:self._client.request("PUT",f"/me/player/volume?volume_percent={max(0,min(100,volume_percent))}")
    def seek_to_position_ms(self,position_ms:int)->None:self._client.request("PUT",f"/me/player/seek?position_ms={max(0,position_ms)}")
    def transfer_playback(self,device_id:str,*,play:bool=True)->None:
        device_id=device_id.strip()
        if not device_id:raise ValueError("device_id cannot be empty")
        self._client.request("PUT","/me/player",body={"device_ids":[device_id],"play":play})
    def saved_tracks(self,*,limit:int=20)->tuple[SpotifyLibraryTrack,...]:
        response=self._client.request_json("GET",f"/me/tracks?{urlencode({'limit':self._limit(limit)})}") or {}
        return tuple(track for item in response.get("items") or [] if isinstance(item,dict) for track in [self._library_track(item.get("track"))] if track is not None)
    def recently_played(self,*,limit:int=20)->tuple[SpotifyLibraryTrack,...]:
        response=self._client.request_json("GET",f"/me/player/recently-played?{urlencode({'limit':self._limit(limit)})}") or {}; tracks=[]
        for item in response.get("items") or []:
            if isinstance(item,dict):
                track=self._library_track(item.get("track"),played_at=item.get("played_at"))
                if track is not None:tracks.append(track)
        return tuple(tracks)
    def playlists(self,*,limit:int=20)->tuple[SpotifyPlaylist,...]:
        """Return playlist summaries owned or followed by the current user."""
        response=self._client.request_json("GET",f"/me/playlists?{urlencode({'limit':self._limit(limit)})}") or {}; playlists=[]
        for item in response.get("items") or []:
            if not isinstance(item,dict):continue
            playlist_id=item.get("id"); name=item.get("name"); uri=item.get("uri")
            if not all(isinstance(value,str) and value for value in (playlist_id,name,uri)):continue
            images=item.get("images") if isinstance(item.get("images"),list) else []; image_url=next((image.get("url") for image in images if isinstance(image,dict) and isinstance(image.get("url"),str)),None); items=item.get("items") if isinstance(item.get("items"),dict) else item.get("tracks") if isinstance(item.get("tracks"),dict) else {}; owner=item.get("owner") if isinstance(item.get("owner"),dict) else {}
            playlists.append(SpotifyPlaylist(playlist_id=playlist_id,name=name,uri=uri,image_url=image_url,item_count=items.get("total") if isinstance(items.get("total"),int) else None,owner_name=owner.get("display_name") if isinstance(owner.get("display_name"),str) else None))
        return tuple(playlists)
    def playlist_tracks(self,playlist_id:str,*,limit:int=20)->tuple[SpotifyLibraryTrack,...]:
        """Return playable tracks from a Spotify playlist."""
        playlist_id=playlist_id.strip()
        if not playlist_id:raise ValueError("playlist_id cannot be empty")
        response=self._client.request_json("GET",f"/playlists/{quote(playlist_id,safe='')}/items?{urlencode({'limit':self._limit(limit)})}") or {}; tracks=[]
        for item in response.get("items") or []:
            if not isinstance(item,dict):continue
            track=self._library_track(item.get("item") if "item" in item else item.get("track"))
            if track is not None:tracks.append(track)
        return tuple(tracks)
    def play_track(self,track_uri:str)->None:
        track_uri=track_uri.strip()
        if not track_uri.startswith("spotify:track:"):raise ValueError("track_uri must be a Spotify track URI")
        self._client.request("PUT","/me/player/play",body={"uris":[track_uri]})
    def _create_state(self,response:dict[str,Any])->SpotifyState:
        item=response.get("item") or {}; album=item.get("album") or {}; artists=item.get("artists") or []; device=response.get("device") or {}; external_urls=item.get("external_urls") or {}; playing=bool(response.get("is_playing")); supports=device.get("supports_volume"); supports=supports if isinstance(supports,bool) else None
        return SpotifyState(is_available=True,is_playing=playing,track_name=item.get("name"),artist_name=self._extract_artist_name(artists),album_name=album.get("name"),track_uri=item.get("uri"),album_art_url=self._extract_album_art_url(album),spotify_url=external_urls.get("spotify"),release_date=album.get("release_date"),device_name=device.get("name"),volume_percent=device.get("volume_percent"),supports_volume=supports,progress_ms=response.get("progress_ms"),duration_ms=item.get("duration_ms"),status_message="Playing" if playing else "Paused")
    @classmethod
    def _library_track(cls,track:object,*,played_at:object=None)->SpotifyLibraryTrack|None:
        if not isinstance(track,dict):return None
        name=track.get("name"); uri=track.get("uri")
        if not isinstance(name,str) or not name or not isinstance(uri,str) or not uri:return None
        album=track.get("album") if isinstance(track.get("album"),dict) else {}; artists=track.get("artists") if isinstance(track.get("artists"),list) else []
        return SpotifyLibraryTrack(name=name,artist_name=cls._extract_artist_name(artists) or "Unknown artist",album_name=album.get("name") if isinstance(album.get("name"),str) else None,uri=uri,album_art_url=cls._extract_album_art_url(album),played_at=played_at if isinstance(played_at,str) else None)
    @staticmethod
    def _limit(limit:int)->int:return max(1,min(50,int(limit)))
    @staticmethod
    def _extract_artist_name(artists:list[dict[str,Any]])->str|None:
        names=[str(a["name"]) for a in artists if isinstance(a,dict) and a.get("name") is not None]; return ", ".join(names) if names else None
    @staticmethod
    def _extract_album_art_url(album:dict[str,Any])->str|None:
        for image in album.get("images") or []:
            if isinstance(image,dict) and isinstance(image.get("url"),str) and image["url"]:return image["url"]
        return None
