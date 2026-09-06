# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import html
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .music_video_if import MusicVideoIf
from .music_video_types import MusicVideo, MusicVideoQuery
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager
from security.secret_manager_if import SecretManagerIf

_YOUTUBE_SEARCH_URL="https://www.googleapis.com/youtube/v3/search"; _YOUTUBE_VIDEOS_URL="https://www.googleapis.com/youtube/v3/videos"
_ISO_8601_DURATION=re.compile(r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$")

@dataclass(frozen=True)
class _Candidate:
    video:MusicVideo; score:int

class YouTubeMusicVideo(MusicVideoIf):
    """Find and present music videos using YouTube."""
    def __init__(self,secret_manager:SecretManagerIf|None=None,*,api_key_secret_name:str="YOUTUBE_API_KEY",max_search_results:int=10,region_code:str="US",host:str="127.0.0.1",port:int=8768,fullscreen:bool=False,chromium_executable:str|None=None,software_rendering:bool=False,window_class:str|None=None,show_return_button:bool=True)->None:
        """Create a YouTube music-video backend.

        @param window_class Optional X11 browser class used by ORC reparenting.
        @param show_return_button Whether the hosted page renders its standalone RETURN button.
        """
        if not 1<=max_search_results<=50:raise ValueError("max_search_results must be between 1 and 50")
        if len(region_code)!=2:raise ValueError("region_code must be a two-letter country code")
        self._secret_manager=secret_manager if secret_manager is not None else EnvironmentVariableSecretManager(); self._api_key_secret_name=api_key_secret_name; self._max_search_results=max_search_results; self._region_code=region_code.upper(); self._host=host; self._port=port; self._fullscreen=fullscreen; self._chromium_executable=chromium_executable; self._software_rendering=software_rendering; self._window_class=window_class; self._show_return_button=show_return_button; self._server=None; self._server_thread=None; self._browser_process=None; self._temporary_directory=None; self._ranked_video_ids=[]
    @property
    def browser_process_id(self)->int|None:
        """Return the active browser PID for X11 embedding."""
        process=self._browser_process; return process.pid if process is not None and process.poll() is None else None
    def find_video(self,query:MusicVideoQuery)->MusicVideo|None:
        api_key=self._get_api_key(); payload=self._get_json(_YOUTUBE_SEARCH_URL,{"part":"snippet","q":f"{query.artist} {query.title} official music video","type":"video","videoEmbeddable":"true","videoSyndicated":"true","maxResults":str(self._max_search_results),"regionCode":self._region_code,"safeSearch":"moderate","key":api_key}); items=payload.get("items",[])
        if not isinstance(items,list) or not items:return None
        ids=[item.get("id",{}).get("videoId") for item in items if isinstance(item,dict)]; ids=[v for v in ids if isinstance(v,str)]; durations,embeddable=self._fetch_video_details(ids,api_key); candidates=[]
        for item in items:
            if not isinstance(item,dict):continue
            identifier=item.get("id"); snippet=item.get("snippet")
            if not isinstance(identifier,dict) or not isinstance(snippet,dict):continue
            video_id=identifier.get("videoId"); title=snippet.get("title"); channel=snippet.get("channelTitle")
            if not all(isinstance(v,str) and v for v in (video_id,title,channel)) or video_id not in embeddable:continue
            title=html.unescape(title); channel=html.unescape(channel); video=MusicVideo(video_id=video_id,title=title,channel_name=channel,thumbnail_url=self._extract_thumbnail_url(snippet),duration_ms=durations.get(video_id),is_official=self._looks_official(title,channel,query.artist)); candidates.append(_Candidate(video,self._score_candidate(video,query)))
        if not candidates:self._ranked_video_ids=[]; return None
        ranked=sorted(candidates,key=lambda c:c.score,reverse=True); self._ranked_video_ids=[c.video.video_id for c in ranked]; return ranked[0].video
    def play_video(self,video:MusicVideo,position_ms:int=0)->bool:
        if not video.video_id:raise ValueError("video.video_id cannot be empty")
        if position_ms<0:raise ValueError("position_ms cannot be negative")
        self.stop_video(); chromium=self._find_chromium()
        if chromium is None:raise RuntimeError("Chromium was not found. Install chromium or provide chromium_executable.")
        self._temporary_directory=tempfile.TemporaryDirectory(prefix="youtube-music-video-"); root=Path(self._temporary_directory.name); profile=root/"chromium-profile"; profile.mkdir(parents=True,exist_ok=True); fallbacks=self._ranked_video_ids if video.video_id in self._ranked_video_ids else [video.video_id]; (root/"index.html").write_text(self._build_player_html(video.video_id,position_ms,fallbacks),encoding="utf-8"); handler=self._make_request_handler(root,close_callback=self.stop_video)
        try:self._server=ThreadingHTTPServer((self._host,self._port),handler)
        except OSError:self._cleanup(); raise
        self._server_thread=threading.Thread(target=self._server.serve_forever,name="youtube-music-video-http",daemon=True); self._server_thread.start(); url=f"http://{self._host}:{self._port}/index.html"; command=[chromium,f"--app={url}",f"--user-data-dir={profile}","--autoplay-policy=no-user-gesture-required","--no-first-run","--disable-session-crashed-bubble"]
        if self._window_class:command.append(f"--class={self._window_class}")
        if self._software_rendering:command.extend(("--disable-gpu","--disable-gpu-compositing","--disable-features=VaapiVideoDecoder,VaapiVideoEncoder"))
        if self._fullscreen:command.append("--start-fullscreen")
        try:self._browser_process=subprocess.Popen(command,start_new_session=True)
        except OSError:self._cleanup(); raise
        return True
    def stop_video(self)->None:
        process=self._browser_process
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGTERM); process.wait(timeout=1.0)
                except (ProcessLookupError,PermissionError,subprocess.TimeoutExpired):
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except (ProcessLookupError,PermissionError):process.kill()
        self._cleanup()
    def is_video_active(self)->bool:return self._browser_process is not None and self._browser_process.poll() is None
    def _fetch_video_details(self,ids:list[str],api_key:str)->tuple[dict[str,int],set[str]]:
        if not ids:return {},set()
        payload=self._get_json(_YOUTUBE_VIDEOS_URL,{"part":"contentDetails,status","id":",".join(ids),"key":api_key}); durations={}; embeddable=set()
        for item in payload.get("items",[]):
            if not isinstance(item,dict):continue
            vid=item.get("id"); details=item.get("contentDetails"); status=item.get("status")
            if not isinstance(vid,str):continue
            if isinstance(status,dict) and status.get("embeddable") is True:embeddable.add(vid)
            if isinstance(details,dict) and isinstance(details.get("duration"),str):
                duration=self._parse_duration_ms(details["duration"])
                if duration is not None:durations[vid]=duration
        return durations,embeddable
    def _get_api_key(self)->str:
        try:return self._secret_manager.require_secret(self._api_key_secret_name)
        except RuntimeError as error:raise RuntimeError(f"The YouTube Data API key is unavailable. Expected secret: {self._api_key_secret_name}") from error
    @staticmethod
    def _score_candidate(video,query):
        title=video.title.casefold(); channel=video.channel_name.casefold(); artist=query.artist.casefold().strip(); track=query.title.casefold().strip(); score=0
        if artist and artist in title:score+=35
        if track and track in title:score+=45
        if "official music video" in title:score+=35
        elif "official video" in title:score+=25
        elif "music video" in title:score+=15
        if video.is_official:score+=25
        if artist and artist in channel:score+=15
        for phrase,penalty in {"official audio":15,"lyrics":12,"lyric video":20,"live":18,"cover":45,"reaction":60,"karaoke":55,"remix":20,"sped up":50,"slowed":50}.items():
            if phrase in title:score-=penalty
        if query.duration_ms is not None and video.duration_ms is not None:
            diff=abs(query.duration_ms-video.duration_ms); score+=25 if diff<=5000 else 15 if diff<=15000 else 5 if diff<=30000 else -30 if diff>=120000 else 0
        return score
    @staticmethod
    def _looks_official(title,channel,artist):
        t=title.casefold(); c=channel.casefold(); a=artist.casefold().strip(); return "official music video" in t or "official video" in t or c.endswith("vevo") or c.endswith(" - topic") or bool(a and a in c)
    @staticmethod
    def _extract_thumbnail_url(snippet):
        thumbnails=snippet.get("thumbnails")
        if not isinstance(thumbnails,dict):return None
        for size in ("maxres","standard","high","medium","default"):
            thumbnail=thumbnails.get(size)
            if isinstance(thumbnail,dict) and isinstance(thumbnail.get("url"),str) and thumbnail["url"]:return thumbnail["url"]
        return None
    @staticmethod
    def _parse_duration_ms(value):
        match=_ISO_8601_DURATION.fullmatch(value)
        if match is None:return None
        return (int(match.group("days") or 0)*86400+int(match.group("hours") or 0)*3600+int(match.group("minutes") or 0)*60+int(match.group("seconds") or 0))*1000
    @staticmethod
    def _get_json(url,parameters):
        request=urllib.request.Request(f"{url}?{urllib.parse.urlencode(parameters)}",headers={"Accept":"application/json"})
        try:
            with urllib.request.urlopen(request,timeout=10) as response:value=json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:raise RuntimeError(f"YouTube API request failed with HTTP {error.code}: {error.read().decode('utf-8',errors='replace')}") from error
        except urllib.error.URLError as error:raise RuntimeError(f"YouTube API request failed: {error.reason}") from error
        except json.JSONDecodeError as error:raise RuntimeError("YouTube API returned invalid JSON") from error
        if not isinstance(value,dict):raise RuntimeError("YouTube API returned an unexpected response")
        return value
    def _find_chromium(self):
        if self._chromium_executable is not None:return self._chromium_executable
        for candidate in ("chromium","chromium-browser","google-chrome","google-chrome-stable"):
            executable=shutil.which(candidate)
            if executable:return executable
        return None
    @staticmethod
    def _make_request_handler(root:Path,*,close_callback:Callable[[],None]):
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(root),**kwargs)
            def do_POST(self):
                if self.path!="/close":self.send_error(404); return
                self.send_response(204); self.end_headers(); threading.Thread(target=close_callback,name="youtube-music-video-close",daemon=True).start()
            def log_message(self,format_string,*args):return
        return Handler
    def _cleanup(self):
        if self._server is not None:self._server.shutdown(); self._server.server_close()
        self._server=None; self._server_thread=None; self._browser_process=None
        if self._temporary_directory is not None:self._temporary_directory.cleanup()
        self._temporary_directory=None
    def _build_player_html(self,video_id,position_ms,fallback_video_ids=None):
        start=position_ms/1000; origin=f"http://{self._host}:{self._port}"; ids=list(dict.fromkeys(fallback_video_ids or [video_id])); ids.remove(video_id) if video_id in ids else None; ids.insert(0,video_id); return_button="<button id='return-to-carui' type='button'>RETURN</button>" if self._show_return_button else ""; return_script="document.getElementById('return-to-carui').addEventListener('click',async()=>{try{await fetch('/close',{method:'POST'});}catch(_error){} window.close();});" if self._show_return_button else ""
        return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>YouTube Music Video</title><style>html,body,#player{{width:100%;height:100%;margin:0;overflow:hidden;background:black}}#message{{position:fixed;left:16px;bottom:16px;z-index:10;display:none;padding:8px 12px;color:white;background:rgba(0,0,0,.72);font-family:sans-serif}}#return-to-carui{{position:fixed;top:16px;right:16px;z-index:20;padding:14px 20px;color:white;background:rgba(0,0,0,.78);font:bold 16px sans-serif}}</style></head><body><div id='player'></div><div id='message'></div>{return_button}<script>const candidateVideoIds={json.dumps(ids)};const startSeconds={start};const playerOrigin={json.dumps(origin)};let candidateIndex=0;let player;{return_script}function msg(t){{let m=document.getElementById('message');m.textContent=t;m.style.display='block'}}function err(e){{candidateIndex++;if(candidateIndex<candidateVideoIds.length){{player.loadVideoById({{videoId:candidateVideoIds[candidateIndex],startSeconds:Math.floor(startSeconds)}});return}}msg('No matching YouTube video is available for in-app playback.')}}function onYouTubeIframeAPIReady(){{player=new YT.Player('player',{{width:'100%',height:'100%',videoId:candidateVideoIds[0],playerVars:{{autoplay:1,controls:1,enablejsapi:1,playsinline:1,rel:0,start:Math.floor(startSeconds),origin:playerOrigin}},events:{{onReady:e=>{{if(startSeconds>0)e.target.seekTo(startSeconds,true);e.target.playVideo()}},onError:err,onAutoplayBlocked:()=>{{player.mute();player.playVideo();setTimeout(()=>player.unMute(),200)}}}}}})}}let s=document.createElement('script');s.src='https://www.youtube.com/iframe_api';document.head.appendChild(s);</script></body></html>"""
    def __enter__(self):return self
    def __exit__(self,exception_type,exception,traceback):self.stop_video()
