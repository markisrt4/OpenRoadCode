# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integrated media hub for the ORC UI shell."""

from __future__ import annotations

import copy
import os
import queue
import tkinter as tk
from collections.abc import Callable

from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from apps.orcUi.orc_theme import ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, DARK
from apps.orcUi.spotify_local_player import SpotifyLocalPlayer, SpotifyPlaybackMode
from apps.orcUi.spotify_state_service import SpotifyStateService
from config.runtime_target import RuntimeTarget, detect_runtime_target
from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.video import MusicVideoController, NetflixPlayer, YouTubeMusicVideo, YouTubePlayer
from frontends.tk.media import SpotifyPlaybackPanel
from frontends.x11 import X11WindowEmbedder
from ui.theme import ThemeMode

BG = DARK["bg"]
PANEL = DARK["panel"]
ACTIVE = DARK["active"]
BORDER = DARK["border"]
TEXT = DARK["text"]
MUTED = DARK["muted"]
MUSIC_VIDEO_PORT = 8770
YOUTUBE_WINDOW_CLASS = "OpenRoadCodeYouTube"
NETFLIX_WINDOW_CLASS = "OpenRoadCodeNetflix"


def _orc_spotify_theme() -> dict:
    theme = copy.deepcopy(SPOTIFY_PANEL_THEME)
    theme["colors"].update({"background":BG,"card_background":PANEL,"card_border":BORDER,"title":TEXT,"subtitle":MUTED,"detail":MUTED,"status":ACCENT_GREEN,"button_background":ACTIVE,"button_foreground":TEXT,"button_active_background":ACCENT_GREEN,"button_active_foreground":BG,"button_disabled_foreground":MUTED,"progress_track":BORDER,"progress_fill":ACCENT_GREEN})
    return theme


class MediaPanel(tk.Frame):
    """ORC-styled media landing page with hosted media applications."""

    def __init__(self,parent:tk.Widget,*,on_back:Callable[[],None],spotify_service:SpotifyStateService,spotify_local_player:SpotifyLocalPlayer,status_callback:Callable[[str],None]|None=None,theme_mode:ThemeMode=ThemeMode.DARK)->None:
        super().__init__(parent,bg=BG); self._on_back=on_back; self._spotify_service=spotify_service; self._spotify_local_player=spotify_local_player; self._status_callback=status_callback or (lambda _message:None); self._theme_mode=theme_mode; self._display=os.environ.get("DISPLAY",":1"); self._view_host:tk.Frame|None=None; self._browser_host:tk.Frame|None=None; self._browser_embedder=X11WindowEmbedder(); self._active_browser:str|None=None; self._netflix_player:NetflixPlayer|None=None; self._youtube_player:YouTubePlayer|None=None; self._spotify_video_controller:MusicVideoController|None=None; self._spotify_refresh_job:str|None=None; self._spotify_panel:SpotifyPlaybackPanel|None=None; self._spotify_mode_buttons:dict[SpotifyPlaybackMode,tk.Button]={}; self._spotify_mode_status:tk.Label|None=None; self._ui_dispatch_queue:queue.SimpleQueue[Callable[[],None]]=queue.SimpleQueue(); self._ui_dispatch_job:str|None=None; self._closed=False; self._build_shell(); self._ui_dispatch_job=self.after(25,self._poll_ui_dispatch); self.show_hub()

    def set_theme_mode(self,theme_mode:ThemeMode)->None:
        if theme_mode is self._theme_mode:return
        self._theme_mode=theme_mode; active_browser=self._active_browser
        if active_browser=="youtube":self.show_youtube()
        elif active_browser=="netflix":self.show_netflix()

    def close(self)->None:
        if self._closed:return
        self._closed=True; self._cancel_spotify_refresh()
        if self._ui_dispatch_job is not None:
            try:self.after_cancel(self._ui_dispatch_job)
            except tk.TclError:pass
            self._ui_dispatch_job=None
        if self._spotify_video_controller is not None:self._spotify_video_controller.stop_video()
        self._stop_embedded_browser()
    def destroy(self)->None:self.close(); super().destroy()

    def show_hub(self)->None:
        self._clear_view(); self._set_title("MEDIA","Music, video, and streaming"); hero=tk.Frame(self._view_host,bg=BG); hero.pack(fill=tk.X,padx=12,pady=(2,4)); tk.Label(hero,text="YOUR MEDIA",bg=BG,fg=TEXT,font=("Sans",22,"bold")).pack(anchor="w"); tk.Label(hero,text="Pick a service and go. No launcher maze required.",bg=BG,fg=MUTED,font=("Sans",10)).pack(anchor="w",pady=(1,0)); grid=tk.Frame(self._view_host,bg=BG); grid.pack(fill=tk.BOTH,expand=True,padx=6,pady=(4,8)); [grid.grid_columnconfigure(column,weight=1,uniform="media") for column in range(3)]; grid.grid_rowconfigure(0,weight=1); cards=(("♫","SPOTIFY","MUSIC","Now playing","Artwork, lyrics, playback controls and music video.","OPEN PLAYER",ACCENT_GREEN,self.show_spotify),("▶","YOUTUBE","VIDEO","Watch anything","Open YouTube inside the ORC media surface.","OPEN YOUTUBE",ACCENT_RED,self.show_youtube),("N","NETFLIX","STREAM","Continue watching","Open Netflix inside ORC using your retained browser profile.","OPEN NETFLIX",ACCENT_BLUE,self.show_netflix)); [self._media_card(grid,*card).grid(row=0,column=column,sticky="nsew",padx=6,pady=4) for column,card in enumerate(cards)]

    def show_spotify(self)->None:
        self._clear_view(); self._set_title("SPOTIFY","Now playing and playback controls",show_media_back=True)
        try:
            self._build_spotify_mode_bar(); self._spotify_service.request_refresh(); target=detect_runtime_target(); video_controller=MusicVideoController(spotify_controller=self._spotify_service.controller,music_video=YouTubeMusicVideo(port=MUSIC_VIDEO_PORT,fullscreen=True,software_rendering=target is RuntimeTarget.LINUX_DEV)); panel=SpotifyPlaybackPanel(self._view_host,music_video_controller=video_controller,image_cache=ImageCache(max_entries=64),lyrics_client=LrclibLyricsClient(),theme=_orc_spotify_theme()); panel.set_playback_request_handler(self._spotify_service); panel.set_track_request_handler(self._spotify_service); panel.set_seek_request_handler(self._spotify_service); panel.set_volume_request_handler(self._spotify_service); panel.pack(fill=tk.BOTH,expand=True,padx=4,pady=4); self._spotify_video_controller=video_controller; self._spotify_panel=panel; self._refresh_spotify()
        except Exception as error:self._show_error("Spotify",error)

    def _build_spotify_mode_bar(self)->None:
        bar=tk.Frame(self._view_host,bg=BG); bar.pack(fill=tk.X,padx=4,pady=(0,4)); tk.Label(bar,text="PLAYBACK",bg=BG,fg=MUTED,font=("Sans",8,"bold")).pack(side=tk.LEFT,padx=(4,8)); self._spotify_mode_buttons={}
        for mode,command in ((SpotifyPlaybackMode.REMOTE,self._spotify_local_player.request_remote),(SpotifyPlaybackMode.PLAYER,self._spotify_local_player.request_player)):
            button=tk.Button(bar,text=mode.value,command=command,bg=ACTIVE,fg=TEXT,activebackground=ACCENT_GREEN,activeforeground=BG,relief=tk.FLAT,bd=0,font=("Sans",9,"bold"),padx=14,pady=5); button.pack(side=tk.LEFT,padx=2); self._spotify_mode_buttons[mode]=button
        self._spotify_mode_status=tk.Label(bar,text="",bg=BG,fg=MUTED,font=("Sans",9)); self._spotify_mode_status.pack(side=tk.LEFT,padx=(10,0)); self._refresh_spotify_mode()

    def _refresh_spotify_mode(self)->None:
        state=self._spotify_local_player.state()
        for mode,button in self._spotify_mode_buttons.items():
            selected=mode is state.mode; button.configure(bg=ACCENT_GREEN if selected else ACTIVE,fg=BG if selected else TEXT,state=tk.DISABLED if state.busy or (mode is SpotifyPlaybackMode.PLAYER and not state.available) else tk.NORMAL)
        if self._spotify_mode_status is not None:self._spotify_mode_status.configure(text=state.message,fg=ACCENT_GREEN if state.mode is SpotifyPlaybackMode.PLAYER and not state.busy else MUTED)

    def show_youtube(self)->None:self._show_embedded_browser(service="YouTube",subtitle="Embedded YouTube kiosk",window_class=YOUTUBE_WINDOW_CLASS,launch=self._launch_youtube)
    def show_netflix(self)->None:self._show_embedded_browser(service="Netflix",subtitle="Embedded Netflix kiosk",window_class=NETFLIX_WINDOW_CLASS,launch=self._launch_netflix)
    def _launch_youtube(self,position,size):self._youtube_player=YouTubePlayer(software_rendering=detect_runtime_target() is RuntimeTarget.LINUX_DEV,dark_mode=self._theme_mode is ThemeMode.DARK); self._youtube_player.play("https://www.youtube.com/",display=self._display,window_position=position,window_size=size); self._active_browser="youtube"
    def _launch_netflix(self,position,size):self._netflix_player=NetflixPlayer(software_rendering=detect_runtime_target() is RuntimeTarget.LINUX_DEV,dark_mode=self._theme_mode is ThemeMode.DARK); self._netflix_player.play("https://www.netflix.com/browse",display=self._display,window_position=position,window_size=size); self._active_browser="netflix"
    def _show_embedded_browser(self,*,service,subtitle,window_class,launch):
        self._clear_view(); self._set_title(service.upper(),subtitle,show_media_back=True)
        try:
            if not X11WindowEmbedder.supported():raise RuntimeError("xdotool is required for embedded media kiosks")
            host=tk.Frame(self._view_host,bg="#000000",highlightthickness=1,highlightbackground=BORDER); host.pack(fill=tk.BOTH,expand=True,padx=4,pady=4); host.bind("<Configure>",self._on_browser_host_resize); self._browser_host=host; self.update_idletasks(); size=(max(1,host.winfo_width()),max(1,host.winfo_height())); position=(host.winfo_rootx(),host.winfo_rooty()); launch(position,size); self.update_idletasks(); self._browser_embedder.embed(0,int(host.winfo_id()),size[0],size[1],window_class=window_class); self._status_callback(f"{service} embedded")
        except Exception as error:self._stop_embedded_browser(); self._show_error(service,error)
    def _on_browser_host_resize(self,event):
        if self._browser_embedder.window_id is not None:self._browser_embedder.resize(max(1,event.width),max(1,event.height))
    def _stop_embedded_browser(self):
        if self._browser_embedder.window_id is not None:
            try:self._browser_embedder.detach(int(self.winfo_toplevel().winfo_id()))
            except (RuntimeError,tk.TclError):self._browser_embedder.clear()
        if self._active_browser=="youtube" and self._youtube_player is not None:self._youtube_player.stop()
        elif self._active_browser=="netflix" and self._netflix_player is not None:self._netflix_player.stop()
        self._active_browser=None; self._browser_host=None
    def _build_shell(self):
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1); self._header=tk.Frame(self,bg=PANEL,highlightthickness=1,highlightbackground=BORDER); self._header.grid(row=0,column=0,sticky="ew",padx=2,pady=(2,6)); self._header.grid_columnconfigure(1,weight=1); self._back_button=tk.Button(self._header,text="‹ HOME",command=self._on_back,bg=PANEL,fg=TEXT,activebackground=ACTIVE,activeforeground=TEXT,relief=tk.FLAT,bd=0,font=("Sans",10,"bold"),padx=10,pady=8); self._back_button.grid(row=0,column=0,rowspan=2,sticky="nsw",padx=(6,10),pady=5); self._title_label=tk.Label(self._header,text="MEDIA",bg=PANEL,fg=TEXT,font=("Sans",16,"bold")); self._title_label.grid(row=0,column=1,sticky="sw",pady=(7,0)); self._subtitle_label=tk.Label(self._header,text="",bg=PANEL,fg=MUTED,font=("Sans",9)); self._subtitle_label.grid(row=1,column=1,sticky="nw",pady=(0,7)); self._media_back=tk.Button(self._header,text="ALL MEDIA",command=self.show_hub,bg=ACTIVE,fg=TEXT,activebackground=BORDER,activeforeground=TEXT,relief=tk.FLAT,bd=0,font=("Sans",9,"bold"),padx=12,pady=7); self._media_back.grid(row=0,column=2,rowspan=2,padx=8,pady=6); self._view_host=tk.Frame(self,bg=BG); self._view_host.grid(row=1,column=0,sticky="nsew")
    def _set_title(self,title,subtitle,*,show_media_back=False):self._title_label.configure(text=title); self._subtitle_label.configure(text=subtitle); self._media_back.grid() if show_media_back else self._media_back.grid_remove()
    def _clear_view(self):
        self._stop_embedded_browser(); self._cancel_spotify_refresh(); self._spotify_panel=None; self._spotify_mode_buttons={}; self._spotify_mode_status=None
        if self._spotify_video_controller is not None:self._spotify_video_controller.stop_video(); self._spotify_video_controller=None
        if self._view_host is not None:
            for child in self._view_host.winfo_children():child.destroy()
    def _cancel_spotify_refresh(self):
        if self._spotify_refresh_job is not None:
            try:self.after_cancel(self._spotify_refresh_job)
            except tk.TclError:pass
            self._spotify_refresh_job=None
    def _refresh_spotify(self):
        panel=self._spotify_panel
        if panel is None or self._closed:return
        try:panel.set_media_state(self._spotify_service.latest_state()); self._refresh_spotify_mode()
        except tk.TclError:return
        self._spotify_refresh_job=self.after(500,self._refresh_spotify)
    def _dispatch_ui(self,callback):self._ui_dispatch_queue.put(callback)
    def _poll_ui_dispatch(self):
        self._ui_dispatch_job=None
        if self._closed:return
        for _ in range(100):
            try:callback=self._ui_dispatch_queue.get_nowait()
            except queue.Empty:break
            try:callback()
            except (RuntimeError,tk.TclError):pass
        self._ui_dispatch_job=self.after(25,self._poll_ui_dispatch)
    def _media_card(self,parent,glyph,title,category,subtitle,detail,action,accent,command):
        card=tk.Frame(parent,bg=PANEL,highlightthickness=1,highlightbackground=BORDER,cursor="hand2"); tk.Frame(card,bg=accent,height=6).pack(fill=tk.X); body=tk.Frame(card,bg=PANEL); body.pack(fill=tk.BOTH,expand=True,padx=16,pady=(14,12)); top=tk.Frame(body,bg=PANEL); top.pack(fill=tk.X); glyph_box=tk.Frame(top,bg=accent,width=48,height=48); glyph_box.pack(side=tk.LEFT); glyph_box.pack_propagate(False); tk.Label(glyph_box,text=glyph,bg=accent,fg=BG,font=("Sans",22,"bold")).pack(fill=tk.BOTH,expand=True); identity=tk.Frame(top,bg=PANEL); identity.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=(12,0)); tk.Label(identity,text=title,bg=PANEL,fg=TEXT,font=("Sans",16,"bold")).pack(anchor="w"); tk.Label(identity,text=category,bg=PANEL,fg=accent,font=("Sans",8,"bold")).pack(anchor="w",pady=(2,0)); tk.Label(body,text=subtitle,bg=PANEL,fg=TEXT,font=("Sans",12,"bold")).pack(anchor="w",pady=(18,5)); tk.Label(body,text=detail,bg=PANEL,fg=MUTED,font=("Sans",9),justify=tk.LEFT,wraplength=220).pack(anchor="w"); button=tk.Button(body,text=f"{action}   ›",command=command,bg=accent,fg=BG,activebackground=accent,activeforeground=BG,relief=tk.FLAT,bd=0,font=("Sans",9,"bold"),padx=12,pady=9,cursor="hand2"); button.pack(fill=tk.X,side=tk.BOTTOM,pady=(14,0)); self._bind_card(card,command); self._bind_hover(card,accent); return card
    @staticmethod
    def _bind_card(widget,command):
        widget.bind("<Button-1>",lambda _event:command())
        for child in widget.winfo_children():
            if not isinstance(child,tk.Button):MediaPanel._bind_card(child,command)
    @staticmethod
    def _bind_hover(card,accent):card.bind("<Enter>",lambda _event:card.configure(highlightbackground=accent,highlightthickness=2)); card.bind("<Leave>",lambda _event:card.configure(highlightbackground=BORDER,highlightthickness=1))
    def _show_error(self,service,error):self._status_callback(f"{service} failed: {error}"); tk.Label(self._view_host,text=f"{service} unavailable\n\n{error}",bg=BG,fg=TEXT,font=("Sans",15,"bold"),justify=tk.CENTER,wraplength=650).place(relx=.5,rely=.5,anchor="center")
