# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native Tk rendering for OpenRoadCode music analysis."""
from __future__ import annotations

import math
import random
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from controllers.audio_analysis.audio_analysis import SpectrumAnalysisMode
from controllers.audio_analysis.music_analysis import MusicAnalysisState
from controllers.audio_analysis.selectable_music_analysis_source import MusicAudioInput
from controllers.music_lighting import MusicLightingPatternId, MusicLightingState
from ui.music_analysis import MusicAnalysisRequestHandlerIf, MusicAnalysisStatus, MusicAnalysisUiIf, MusicAnalysisUiState
from ui.music_lighting import MusicLightingRequestHandlerIf, MusicLightingUiIf
from ui.music_visualizer import KickMode, MusicVisualizationMode, MusicVisualizerRequestHandlerIf, MusicVisualizerUiIf, SongRecognitionUiState

_MODE_LABELS={MusicVisualizationMode.SPECTRUM:"Spectrum",MusicVisualizationMode.ORBITING_PLANETS:"Orbiting Planets",MusicVisualizationMode.ELECTRIC_FREEWAY:"Electric Freeway",MusicVisualizationMode.EXPLOSION_FIELD:"Explosion Field",MusicVisualizationMode.STAR_DANCE:"Star Dance",MusicVisualizationMode.ELECTRIC_RINGS:"Electric Rings",MusicVisualizationMode.NEON_RIBBON:"Neon Ribbon",MusicVisualizationMode.KALEIDOSCOPE:"Kaleidoscope"}
_LABEL_MODES={label:mode for mode,label in _MODE_LABELS.items()}
_ANALYSIS_LABELS={SpectrumAnalysisMode.NATIVE:"Native",SpectrumAnalysisMode.NORMALIZED:"Normalized",SpectrumAnalysisMode.HYBRID:"Hybrid"}
_LABEL_ANALYSIS={label:mode for mode,label in _ANALYSIS_LABELS.items()}
_PATTERN_LABELS={MusicLightingPatternId.SPECTRUM_FLOW:"Spectrum Flow",MusicLightingPatternId.BEAT_PULSE:"Beat Pulse",MusicLightingPatternId.PERCUSSION:"Percussion",MusicLightingPatternId.COLOR_WAVE:"Color Wave",MusicLightingPatternId.AMBIENT:"Ambient"}
_LABEL_PATTERNS={label:pattern for pattern,label in _PATTERN_LABELS.items()}
_INPUT_LABELS={MusicAudioInput.SYSTEM_AUDIO:"System Audio",MusicAudioInput.EXTERNAL_INPUT:"External Input"}
_LABEL_INPUTS={label:value for value,label in _INPUT_LABELS.items()}


def _fit_image_size(container_width:int,container_height:int,image_width:int,image_height:int)->tuple[int,int]:
    """Fit an image inside a canvas while always returning valid dimensions."""
    available_width=max(1,int(container_width*.92));available_height=max(1,int(container_height*.94))
    scale=min(available_width/max(1,image_width),available_height/max(1,image_height))
    return max(1,int(image_width*scale)),max(1,int(image_height*scale))

class MusicVisualizerPanel(tk.Frame,MusicAnalysisUiIf,MusicVisualizerUiIf,MusicLightingUiIf):
    def __init__(self,parent:tk.Misc,artwork_provider=None)->None:
        super().__init__(parent,bg="#0b0d10");self._handler:MusicVisualizerRequestHandlerIf|None=None;self._analysis_handler:MusicAnalysisRequestHandlerIf|None=None;self._lighting_handler:MusicLightingRequestHandlerIf|None=None;self._fullscreen_action=None;self._play_song_action=None;self._artwork_provider=artwork_provider;self._song=None;self._song_art_photo=None;self._state:MusicAnalysisState|None=None;self._phase=0.;self._visualization_mode=MusicVisualizationMode.SPECTRUM;self._mode=tk.StringVar(value=_MODE_LABELS[self._visualization_mode]);self._spectrum_style=tk.StringVar(value="Classic Analyzer");self._analysis_mode=tk.StringVar(value=_ANALYSIS_LABELS[SpectrumAnalysisMode.HYBRID]);self._sensitivity=tk.DoubleVar(value=100.);self._lighting=tk.BooleanVar(value=False);self._lighting_pattern=tk.StringVar(value=_PATTERN_LABELS[MusicLightingPatternId.SPECTRUM_FLOW]);self._lighting_intensity=tk.DoubleVar(value=75.);self._kick_mode=tk.StringVar(value=KickMode.SINGLE.value);self._stars=[(random.random(),random.random(),random.uniform(.5,1.5)) for _ in range(70)];self._particles=[];self._pulse={name:0. for name in ("kick","snare","tom_low","tom_mid","tom_high","cymbal")};self._drum_source=Image.open(Path(__file__).resolve().parents[3]/"apps/carUi/assets/drum-set-no-numbers.png").convert("RGBA");self._drum_image=None;self._drum_image_size=(0,0);self._drum_sprites=[];self._drum_sprite_cache={};self._build()
    def set_request_handler(self,handler):self._handler=handler
    def set_music_analysis_request_handler(self,handler):self._analysis_handler=handler
    def set_music_lighting_request_handler(self,handler):self._lighting_handler=handler
    def set_fullscreen_action(self,callback):self._fullscreen_action=callback
    def set_play_song_action(self,callback):self._play_song_action=callback
    def set_fullscreen_status(self,status):self._fullscreen_button.configure(text="↗  VIEW FULLSCREEN" if status is None else status)
    def _build(self):
        self._audio_input=tk.StringVar(value=_INPUT_LABELS[MusicAudioInput.SYSTEM_AUDIO])
        bg="#070b0f";card="#0d141b";border="#263746";muted="#91a0ad";green="#6ee444"
        self.configure(bg=bg);self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(2,weight=1)
        controls=tk.Frame(self,bg=card,highlightbackground=border,highlightthickness=1,padx=10,pady=7);controls.grid(row=0,column=0,sticky="ew",padx=6,pady=(4,6))
        self._audio_button=tk.Button(controls,text="■  STOP AUDIO",command=self._toggle_capture,bg="#251014",fg="#ff4c54",activebackground="#35151a",activeforeground="#ff747a",relief="flat",padx=12,pady=7,font=("TkDefaultFont",10,"bold"));self._audio_button.pack(side="left")
        self._status=tk.Label(controls,text="● SYSTEM AUDIO · STARTING",bg=card,fg=green,font=("TkDefaultFont",10,"bold"));self._status.pack(side="left",padx=8)
        input_picker=ttk.Combobox(controls,textvariable=self._audio_input,values=tuple(_INPUT_LABELS.values()),state="readonly",width=14);input_picker.pack(side="left",padx=(2,8));input_picker.bind("<<ComboboxSelected>>",self._audio_input_changed)
        sens=tk.Scale(controls,from_=25,to=200,orient="horizontal",showvalue=True,length=125,bg=card,fg="white",troughcolor="#26323d",activebackground=green,highlightthickness=0,variable=self._sensitivity,command=lambda v:self._analysis_handler and self._analysis_handler.request_sensitivity(float(v)/100.));sens.pack(side="right");tk.Label(controls,text="SENSITIVITY",bg=card,fg=muted,font=("TkDefaultFont",8,"bold")).pack(side="right")
        hero=tk.Frame(self,bg=card,highlightbackground=border,highlightthickness=1,padx=8,pady=7);hero.grid(row=1,column=0,sticky="ew",padx=6,pady=(0,6));hero.grid_columnconfigure(0,weight=1)
        hero_head=tk.Frame(hero,bg=card);hero_head.grid(row=0,column=0,sticky="ew");tk.Label(hero_head,text="VISUALIZER TYPE",bg=card,fg="white",font=("TkDefaultFont",9,"bold")).pack(side="left")
        combo=ttk.Combobox(hero_head,textvariable=self._mode,values=tuple(_MODE_LABELS.values()),state="readonly",width=20);combo.pack(side="left",padx=8);combo.bind("<<ComboboxSelected>>",self._mode_changed)
        self._fullscreen_button=tk.Button(hero_head,text="↗  VIEW FULLSCREEN",command=self._open_fullscreen,bg="#19232d",fg="white",activebackground="#263746",relief="flat",padx=12,pady=5);self._fullscreen_button.pack(side="right")
        self._embedded_canvas=tk.Canvas(hero,bg="#020509",highlightthickness=0,height=1);self._canvas=self._embedded_canvas;self._fullscreen_window=None
        lower=tk.Frame(self,bg=bg);lower.grid(row=2,column=0,sticky="nsew",padx=6,pady=(0,6));lower.grid_columnconfigure(0,weight=5);lower.grid_columnconfigure(1,weight=4);lower.grid_columnconfigure(2,weight=3);lower.grid_rowconfigure(0,weight=1)
        drums_card=tk.Frame(lower,bg=card,highlightbackground=border,highlightthickness=1,padx=7,pady=6);drums_card.grid(row=0,column=0,sticky="nsew",padx=(0,3));drums_card.grid_rowconfigure(1,weight=1);drums_card.grid_columnconfigure(0,weight=1)
        drum_head=tk.Frame(drums_card,bg=card);drum_head.grid(row=0,column=0,sticky="ew");tk.Label(drum_head,text="PERCUSSION  (Drum Kit)",bg=card,fg="white",font=("TkDefaultFont",10,"bold")).pack(side="left")
        for text,value in (("DOUBLE KICK",KickMode.DOUBLE.value),("SINGLE KICK",KickMode.SINGLE.value)):tk.Radiobutton(drum_head,text=text,value=value,variable=self._kick_mode,command=self._kick_changed,bg=card,fg="#b8c4ce",selectcolor="#29461f",activebackground=card,activeforeground="white",indicatoron=False,relief="flat",padx=7,pady=3,font=("TkDefaultFont",7,"bold")).pack(side="right",padx=2)
        self._drums=tk.Canvas(drums_card,bg="#080c10",highlightthickness=0,height=115);self._drums.grid(row=1,column=0,sticky="nsew")
        spectrum_card=tk.Frame(lower,bg=card,highlightbackground=border,highlightthickness=1,padx=7,pady=6);spectrum_card.grid(row=0,column=1,sticky="nsew",padx=(3,0));spectrum_card.grid_rowconfigure(1,weight=1);spectrum_card.grid_columnconfigure(0,weight=1)
        spectrum_head=tk.Frame(spectrum_card,bg=card);spectrum_head.grid(row=0,column=0,sticky="ew");tk.Label(spectrum_head,text="SPECTRUM",bg=card,fg="white",font=("TkDefaultFont",10,"bold")).pack(side="left");analysis=ttk.Combobox(spectrum_head,textvariable=self._analysis_mode,values=tuple(_ANALYSIS_LABELS.values()),state="readonly",width=10);analysis.pack(side="right");analysis.bind("<<ComboboxSelected>>",self._analysis_mode_changed);ttk.Combobox(spectrum_head,textvariable=self._spectrum_style,values=("Classic Analyzer","Prismatic Ridge","Neon Bars","Mirrored Wave"),state="readonly",width=15).pack(side="right",padx=5)
        self._spectrum_canvas=tk.Canvas(spectrum_card,bg="#050a0e",highlightthickness=0,height=135);self._spectrum_canvas.grid(row=1,column=0,sticky="nsew",pady=(5,0))
        song_card=tk.Frame(lower,bg=card,highlightbackground=border,highlightthickness=1,padx=10,pady=8);song_card.grid(row=0,column=2,sticky="nsew",padx=(6,0));song_card.grid_columnconfigure(0,weight=1);self._song_card=song_card
        self._song_heading=tk.Label(song_card,text="SONG RECOGNITION",bg=card,fg="white",font=("TkDefaultFont",10,"bold"));self._song_heading.grid(row=0,column=0,sticky="w")
        self._song_art=tk.Label(song_card,bg=card);self._song_art.grid(row=1,column=0,pady=(5,2))
        self._song_title=tk.Label(song_card,text="No song identified",bg=card,fg="#f4f7f9",font=("TkDefaultFont",13,"bold"),anchor="w",justify="left",wraplength=190);self._song_title.grid(row=2,column=0,sticky="ew",pady=(4,3))
        self._song_artist=tk.Label(song_card,text="",bg=card,fg="#b9c5cf",anchor="w",justify="left",wraplength=190);self._song_artist.grid(row=3,column=0,sticky="ew")
        self._song_album=tk.Label(song_card,text="",bg=card,fg=muted,anchor="w",justify="left",wraplength=190);self._song_album.grid(row=4,column=0,sticky="ew",pady=(3,0))
        self._now=tk.Label(song_card,text="Checking provider…",bg=card,fg=muted,anchor="w",justify="left",wraplength=190);self._now.grid(row=5,column=0,sticky="sew",pady=(8,6));song_card.grid_rowconfigure(5,weight=1)
        self._identify=tk.Button(song_card,text="IDENTIFY SONG",command=lambda:self._handler and self._handler.request_song_recognition(),bg="#19232d",fg="white",activebackground="#263746",relief="flat",pady=8,font=("TkDefaultFont",9,"bold"));self._identify.grid(row=6,column=0,sticky="ew")
        self._spotify_play=tk.Button(song_card,text="▶  PLAY IN SPOTIFY",command=self._play_recognized_song,bg="#1db954",fg="white",activebackground="#159643",relief="flat",pady=6,font=("TkDefaultFont",8,"bold"));self._spotify_play.grid(row=7,column=0,sticky="ew",pady=(6,0));self._spotify_play.grid_remove()
        footer=tk.Frame(self,bg=card,highlightbackground=border,highlightthickness=1,padx=9,pady=5);footer.grid(row=3,column=0,sticky="ew",padx=6,pady=(0,4));tk.Checkbutton(footer,text="MUSIC LIGHTING",variable=self._lighting,command=self._lighting_enabled_changed,bg=card,fg="white",selectcolor="#25431e",activebackground=card).pack(side="left");pattern=ttk.Combobox(footer,textvariable=self._lighting_pattern,values=tuple(_PATTERN_LABELS.values()),state="readonly",width=15);pattern.pack(side="left",padx=7);pattern.bind("<<ComboboxSelected>>",self._lighting_pattern_changed);tk.Label(footer,text="INTENSITY",bg=card,fg=muted).pack(side="left");tk.Scale(footer,from_=0,to=100,orient="horizontal",showvalue=False,length=100,bg=card,highlightthickness=0,variable=self._lighting_intensity,command=self._lighting_intensity_changed).pack(side="left");tk.Button(footer,text="CONFIGURE →",command=self._configure_lighting,bg="#19232d",fg="white",relief="flat").pack(side="right")
    def _open_fullscreen(self):
        if self._fullscreen_action is not None:
            self._fullscreen_action();return
        if self._fullscreen_window is not None:
            self._fullscreen_window.lift();return
        window=tk.Toplevel(self);window.configure(bg="#020509");window.attributes("-fullscreen",True);window.title("Music Visualizer");canvas=tk.Canvas(window,bg="#020509",highlightthickness=0);canvas.pack(fill="both",expand=True);toolbar=tk.Frame(window,bg="#101820",highlightbackground="#334655",highlightthickness=1,padx=8,pady=7);toolbar.place(relx=.02,rely=.025,anchor="nw");tk.Label(toolbar,text="VISUALIZER",bg="#101820",fg="#9dabb7",font=("TkDefaultFont",9,"bold")).pack(side="left");picker=ttk.Combobox(toolbar,textvariable=self._mode,values=tuple(_MODE_LABELS.values()),state="readonly",width=20);picker.pack(side="left",padx=(8,0));picker.bind("<<ComboboxSelected>>",self._mode_changed);close=tk.Button(window,text="✕  EXIT FULLSCREEN",command=self._close_fullscreen,bg="#141d25",fg="white",activebackground="#263746",relief="flat",padx=14,pady=8);close.place(relx=.98,rely=.025,anchor="ne");window.bind("<Escape>",lambda _event:self._close_fullscreen());window.protocol("WM_DELETE_WINDOW",self._close_fullscreen);self._fullscreen_window=window;self._canvas=canvas;self._draw()
    def _close_fullscreen(self):
        window=self._fullscreen_window;self._fullscreen_window=None;self._canvas=self._embedded_canvas
        if window is not None:window.destroy()
    def close(self):self._close_fullscreen()
    def _toggle_capture(self):
        if not self._analysis_handler:return
        if self._audio_button.cget("text").startswith("■"):self._analysis_handler.stop()
        else:self._analysis_handler.start()
    def set_configure_lighting_action(self,callback):self._configure_lighting_action=callback
    def _configure_lighting(self):
        callback=getattr(self,"_configure_lighting_action",None)
        if callback:callback()
    def _lighting_enabled_changed(self):
        if self._lighting_handler:self._lighting_handler.request_enabled(self._lighting.get())
    def _lighting_pattern_changed(self,_event=None):
        if self._lighting_handler:self._lighting_handler.request_pattern(_LABEL_PATTERNS[self._lighting_pattern.get()])
    def _lighting_intensity_changed(self,value):
        if self._lighting_handler:self._lighting_handler.request_intensity(float(value)/100.)
    def set_music_lighting_state(self,state:MusicLightingState)->None:self._lighting.set(state.enabled);self._lighting_pattern.set(_PATTERN_LABELS[state.pattern]);self._lighting_intensity.set(round(state.intensity*100))
    def _mode_changed(self,_event=None):
        if self._handler:self._handler.request_visualization_mode(_LABEL_MODES.get(self._mode.get(),MusicVisualizationMode.SPECTRUM))
    def _analysis_mode_changed(self,_event=None):
        if self._analysis_handler:self._analysis_handler.request_spectrum_mode(_LABEL_ANALYSIS.get(self._analysis_mode.get(),SpectrumAnalysisMode.HYBRID))
    def _audio_input_changed(self,_event=None):
        if self._analysis_handler:self._analysis_handler.request_audio_input(_LABEL_INPUTS.get(self._audio_input.get(),MusicAudioInput.SYSTEM_AUDIO))
    def _kick_changed(self):
        if self._handler:self._handler.request_kick_mode(KickMode(self._kick_mode.get()))
    def set_analysis_state(self,state):
        self._state=state;self._phase+=.07+state.audio.level*.12
        for name in self._pulse:self._pulse[name]=max(getattr(state.percussion,name),self._pulse[name]*.72)
        self._draw();self._draw_drums();self._draw_spectrum_panel()
    def set_analysis_ui_state(self,state:MusicAnalysisUiState)->None:
        self._sensitivity.set(round(state.sensitivity*100));self._analysis_mode.set(_ANALYSIS_LABELS[state.spectrum_mode]);self._audio_input.set(_INPUT_LABELS[state.audio_input]);parts=[state.status.value.upper()]
        if state.calibrated:parts.append("ZEROIZED")
        if state.status is MusicAnalysisStatus.ZEROIZING:parts.append("KEEP MUSIC OFF")
        if state.error:parts.append(state.error)
        active=state.status in (MusicAnalysisStatus.ACTIVE,MusicAnalysisStatus.ZEROIZING);self._audio_button.configure(text="■  STOP AUDIO" if active else "▶  START AUDIO",fg="#ff4c54" if active else "#75e34c");source=_INPUT_LABELS[state.audio_input].upper();self._status.configure(text=(f"● {source} · " if active else f"○ {source} · ")+"  ·  ".join(parts),fg="#75e34c" if active else "#ff5964" if state.error else "#91a0ad")
    def set_song(self,song):
        self._song=song;self._song_art.configure(image="");self._song_art_photo=None
        if song is None:self._song_title.configure(text="No song identified");self._song_artist.configure(text="");self._song_album.configure(text="");self._spotify_play.grid_remove();return
        self._song_title.configure(text=song.title);self._song_artist.configure(text=" · ".join(song.artists) or "Unknown artist");self._song_album.configure(text=song.album or "")
        if song.spotify_uri:self._spotify_play.grid()
        else:self._spotify_play.grid_remove()
        if song.artwork_url and self._artwork_provider:threading.Thread(target=self._load_song_art,args=(song.artwork_url,),name="recognition-artwork",daemon=True).start()
    def _load_song_art(self,url):
        try:image=self._artwork_provider.get(url,width=82,height=82)
        except Exception:return
        self.after(0,lambda:self._apply_song_art(url,image))
    def _apply_song_art(self,url,image):
        if self._song is None or self._song.artwork_url!=url:image.close();return
        self._song_art_photo=ImageTk.PhotoImage(image);image.close();self._song_art.configure(image=self._song_art_photo)
    def _play_recognized_song(self):
        if self._song is not None and self._play_song_action:self._play_song_action(self._song)
    def set_song_recognition_state(self,state):
        enabled=state.configured and state.ready and not state.recognizing
        self._identify.configure(state="normal" if enabled else "disabled")
        waiting=state.configured and not state.ready and not state.recognizing
        song_bg="#090d11" if waiting else "#0d141b";self._song_card.configure(bg=song_bg)
        self._song_heading.configure(bg=song_bg,fg="#68747e" if waiting else "white")
        self._song_title.configure(bg=song_bg,fg="#68747e" if waiting else "#f4f7f9")
        self._song_artist.configure(bg=song_bg,fg="#68747e" if waiting else "#b9c5cf")
        self._song_album.configure(bg=song_bg,fg="#68747e" if waiting else "#91a0ad")
        self._now.configure(bg=song_bg)
        self._now.configure(text="Listening to recent audio…" if state.recognizing else ("Unconfigured · set ACRCLOUD credentials" if not state.configured else state.message or f"{state.provider or 'Recognizer'} ready"),fg="#ff6972" if state.message and state.message.startswith("Recognition failed") else "#66727c" if waiting else "#91a0ad")
    def set_visualization_mode(self,m):self._visualization_mode=m;self._mode.set(_MODE_LABELS[m])
    def _draw(self):
        if not self._state:return
        c=self._canvas;c.delete("all");w,h=max(2,c.winfo_width()),max(2,c.winfo_height());{MusicVisualizationMode.ORBITING_PLANETS:self._draw_planets,MusicVisualizationMode.ELECTRIC_FREEWAY:self._draw_freeway,MusicVisualizationMode.EXPLOSION_FIELD:self._draw_explosion,MusicVisualizationMode.STAR_DANCE:self._draw_stars,MusicVisualizationMode.ELECTRIC_RINGS:self._draw_rings,MusicVisualizationMode.NEON_RIBBON:self._draw_ribbon,MusicVisualizationMode.KALEIDOSCOPE:self._draw_kaleidoscope}.get(self._visualization_mode,self._draw_spectrum)(w,h)
    def _draw_drums(self):
        c=self._drums;c.delete("all");w=max(2,c.winfo_width());h=max(2,c.winfo_height());cym=self._pulse["cymbal"]
        target_w,target_h=_fit_image_size(w,h,self._drum_source.width,self._drum_source.height)
        if self._drum_image_size!=(target_w,target_h):self._drum_image=ImageTk.PhotoImage(self._drum_source.resize((target_w,target_h),Image.Resampling.LANCZOS));self._drum_image_size=(target_w,target_h);self._drum_sprite_cache.clear()
        left=(w-target_w)/2;top=(h-target_h)/2;c.create_image(w/2,h/2,image=self._drum_image)
        self._drum_sprites=[]
        def pulse_sprite(box,key,amount=.34):
            p=min(1.,self._pulse[key]*2.5)
            if p<.015:return
            x0,y0,x1,y1=box;base_w=(x1-x0)*target_w/self._drum_source.width;base_h=(y1-y0)*target_h/self._drum_source.height;step=max(1,min(6,round(p*6)));cache_key=(target_w,target_h,box,step,amount);sprite=self._drum_sprite_cache.get(cache_key)
            if sprite is None:
                grow=1+(step/6)*amount;crop=self._drum_source.crop((x0,y0,x1,y1));sprite=ImageTk.PhotoImage(crop.resize((max(2,int(base_w*grow)),max(2,int(base_h*grow))),Image.Resampling.BILINEAR));self._drum_sprite_cache[cache_key]=sprite
            self._drum_sprites.append(sprite)
            cx=left+(x0+x1)*.5*target_w/self._drum_source.width;cy=top+(y0+y1)*.5*target_h/self._drum_source.height;c.create_image(cx,cy,image=sprite)
        pulse_sprite((300,330,660,725),"kick",.24);pulse_sprite((105,300,365,590),"tom_low",.28);pulse_sprite((220,145,475,385),"tom_high",.32);pulse_sprite((490,150,730,380),"tom_mid",.32);pulse_sprite((555,315,800,515),"snare",.34);pulse_sprite((20,45,420,190),"cymbal",.25);pulse_sprite((650,250,920,365),"cymbal",.25)
        def reactive_head(nx,ny,nrx,nry,key,color,label):
            p=self._pulse[key];x=left+nx*target_w;y=top+ny*target_h;rx=nrx*target_w*(1+p*.34);ry=nry*target_h*(1+p*.34)
            if p>.04:c.create_oval(x-rx,y-ry,x+rx,y+ry,outline=color,width=2+int(p*6));c.create_oval(x-rx*1.12,y-ry*1.12,x+rx*1.12,y+ry*1.12,outline=self._darken(color,.55),width=1+int(p*3))
            c.create_text(x,y,text=label,fill="#f4f6f8",font=("TkDefaultFont",7,"bold"))
        reactive_head(.50,.70,.18,.22,"kick","#ff4939","KICK")
        if self._kick_mode.get()==KickMode.DOUBLE.value:reactive_head(.67,.73,.14,.18,"kick","#ff4939","KICK R")
        reactive_head(.26,.48,.12,.08,"tom_low","#ffe138","TOM L");reactive_head(.39,.32,.105,.075,"tom_high","#32c7f2","TOM H");reactive_head(.61,.32,.105,.075,"tom_mid","#50df58","TOM M");reactive_head(.72,.50,.11,.065,"snare","#ff9c27","SNARE")
        if cym>.04:
            for nx,ny,rx in ((.21,.14,.19),(.79,.38,.13)):
                x=left+nx*target_w;y=top+ny*target_h;grow=1+cym*.28;c.create_oval(x-rx*target_w*grow,y-.025*target_h*grow,x+rx*target_w*grow,y+.025*target_h*grow,outline="#ffd75d",width=2+int(cym*5))
    @property
    def a(self):return self._state.audio
    def _draw_spectrum(self,w,h):
        vals=self.a.spectrum or (0.,)*24;gap=max(2,w/420);bw=max(2,(w-gap*(len(vals)+1))/len(vals));base=h*.88
        for i,v in enumerate(vals):x=gap+i*(bw+gap);top=base-v*(h*.72);color=self._gradient(i/max(1,len(vals)-1));self._canvas.create_rectangle(x-2,top-3,x+bw+2,base+3,fill=self._darken(color,.32),outline="");self._canvas.create_rectangle(x,top,x+bw,base,fill=color,outline="");self._canvas.create_oval(x,top-2,x+bw,top+3,fill="#e9ffff",outline="")
        self._canvas.create_line(0,base,w,base,fill="#2b4254",width=2)
    def _draw_spectrum_panel(self):
        c=self._spectrum_canvas;c.delete("all");w,h=max(2,c.winfo_width()),max(2,c.winfo_height());vals=self.a.spectrum or (0.,)*24;base=h-22;chart_h=max(20,base-5)
        for i in range(1,6):y=base-i*chart_h/5;c.create_line(0,y,w,y,fill="#142431")
        style=self._spectrum_style.get();points=[]
        for i,v in enumerate(vals):points.extend((i*w/max(1,len(vals)-1),base-v*chart_h))
        if style=="Classic Analyzer":
            gap=max(1,w/300);bw=max(2,(w-gap*(len(vals)+1))/len(vals));segments=12
            for i,v in enumerate(vals):
                x=gap+i*(bw+gap);lit=int(max(0,min(1,v))*segments+.5)
                for segment in range(segments):
                    y1=base-segment*chart_h/segments-1;y0=base-(segment+1)*chart_h/segments+1;ratio=segment/max(1,segments-1)
                    color="#36d34a" if ratio<.55 else "#e2d82f" if ratio<.72 else "#f39a22" if ratio<.88 else "#ef3f35"
                    c.create_rectangle(x,y0,x+bw,y1,fill=color if segment<lit else self._darken(color,.16),outline="")
        elif style=="Prismatic Ridge":
            for i,v in enumerate(vals):
                x0=i*w/len(vals);x1=(i+1)*w/len(vals);top=base-v*chart_h;color=self._gradient(i/max(1,len(vals)-1));c.create_rectangle(x0,top,x1+1,base,fill=self._darken(color,.42),outline="");c.create_line(x0,top,x1,top,fill=color,width=2)
            c.create_line(*points,fill="#f4fbff",width=1,smooth=True)
        elif style=="Mirrored Wave":
            mid=h/2;wave=[]
            for i,v in enumerate(vals):x=i*w/max(1,len(vals)-1);wave.extend((x,mid-v*(h*.40)))
            c.create_line(*wave,fill="#45eaff",width=4,smooth=True);c.create_line(*(sum(([wave[i],h-wave[i+1]] for i in range(0,len(wave),2)),[])),fill="#c34cff",width=3,smooth=True)
        else:
            gap=2;bw=max(2,(w-gap*(len(vals)+1))/len(vals))
            for i,v in enumerate(vals):x=gap+i*(bw+gap);y=base-v*chart_h;color=self._gradient(i/max(1,len(vals)-1));c.create_rectangle(x,y,x+bw,base,fill=color,outline="")
        frequencies=(31,41,54,70,92,120,157,205,268,350,457,597,780,1000,1300,1700,2200,2900,3800,5000,6500,8500,11000,16000)
        for i,frequency in enumerate(frequencies):
            if i%3 and i!=len(frequencies)-1:continue
            label=f"{frequency//1000}k" if frequency>=1000 and frequency%1000==0 else (f"{frequency/1000:.1f}k" if frequency>=1000 else str(frequency));c.create_text((i+.5)*w/len(frequencies),h-9,text=label,fill="#93a2ae",font=("TkDefaultFont",6))
        c.create_text(w-3,h-9,text="Hz",anchor="e",fill="#c6d0d8",font=("TkDefaultFont",6,"bold"))
    def _draw_planets(self,w,h):
        cx,cy=w/2,h/2
        for sx,sy,size in self._stars:self._canvas.create_oval(sx*w,sy*h,sx*w+size,sy*h+size,fill="#b9d8ff",outline="")
        sun=15+20*self.a.level;self._canvas.create_oval(cx-sun,cy-sun,cx+sun,cy+sun,fill="#ffc24b",outline="#fff1a8")
        for radius,speed,e,color in ((.22,.85,self.a.bass,"#55aaff"),(.34,-1.25,self.a.mid,"#ff5d91"),(.45,.42,self.a.treble,"#76ef78")):rr=min(w,h)*radius;a=self._phase*speed;x=cx+math.cos(a)*rr;y=cy+math.sin(a)*rr*.55;pr=6+e*12;self._canvas.create_oval(x-pr,y-pr,x+pr,y+pr,fill=color,outline="white")
    def _draw_freeway(self,w,h):
        horizon=h*.27;cx=w*.5;self._canvas.create_polygon(cx-w*.07,horizon,cx+w*.07,horizon,w*.94,h,w*.06,h,fill="#07141b",outline="#21a8df")
        for lane in (-.5,0,.5):self._canvas.create_line(cx+lane*w*.07,horizon,cx+lane*w*.62,h,fill="#45c9ff",width=2)
        for i in range(7):z=(i*.17+self._phase*.018)%1;y=horizon+z*z*(h-horizon);x=cx+(i-3)*w*.055*z;cw=5+z*17+self.a.bass*7;self._canvas.create_rectangle(x-cw,y-cw*.25,x+cw,y+cw*.25,outline=self._gradient(i*.14+self._phase*.01),width=2)
    def _draw_explosion(self,w,h):
        cx,cy=w/2,h/2
        if self.a.bass>.65 and len(self._particles)<100:self._particles.extend((random.random()*math.tau,random.uniform(.7,2.5),0.) for _ in range(15))
        nxt=[]
        for ang,speed,age in self._particles:
            age+=.03;r=age*min(w,h)*speed
            if age<1:x=cx+math.cos(ang)*r;y=cy+math.sin(ang)*r;s=max(1,5*(1-age));self._canvas.create_oval(x-s,y-s,x+s,y+s,fill="#ffb02e",outline="");nxt.append((ang,speed,age))
        self._particles=nxt;p=15+self.a.bass*50;self._canvas.create_oval(cx-p,cy-p,cx+p,cy+p,outline="#ff5528",width=4)
    def _draw_stars(self,w,h):
        for sx,sy,size in self._stars:x=((sx-.5)*(1+self.a.level*.7)+.5)*w;y=((sy-.5)*(1+self.a.level*.7)+.5)*h;r=size*(1+self.a.treble*3);self._canvas.create_oval(x-r,y-r,x+r,y+r,fill=self._gradient(sx+self._phase*.01),outline="")
    def _draw_rings(self,w,h):
        cx,cy=w/2,h/2
        for i,v in enumerate((self.a.bass,self.a.mid,self.a.treble,self.a.level)):
            r=min(w,h)*(.12+i*.105)*(1+v*.28);color=self._gradient(i*.23+self._phase*.012)
            for glow,width in ((18,"#111b25"),(10,self._darken(color,.30)),(3+int(v*5),color)):self._canvas.create_oval(cx-r,cy-r*.72,cx+r,cy+r*.72,outline=width,width=glow)
        core=12+self.a.bass*42;self._canvas.create_oval(cx-core,cy-core,cx+core,cy+core,fill="#f7fbff",outline="#6cf5ff",width=4)
    def _draw_ribbon(self,w,h):
        vals=self.a.spectrum or (0.,)*24
        for lane in range(7,-1,-1):
            pts=[];offset=(lane-3.5)*h*.035
            for i,v in enumerate(vals):pts.extend((i*w/max(1,len(vals)-1),h*.53+offset+math.sin(self._phase+i*.48+lane*.22)*h*.055-v*h*(.20+lane*.012)))
            color=self._gradient(lane/8+self._phase*.01);self._canvas.create_line(*pts,fill=self._darken(color,.22),width=9,smooth=True);self._canvas.create_line(*pts,fill=color,width=2+int(self.a.treble*3),smooth=True)
    def _draw_kaleidoscope(self,w,h):
        vals=self.a.spectrum or (0.,)*24;cx,cy=w/2,h/2;arms=12;step=min(w,h)/20
        for ring,v in enumerate(vals[::2]):
            radius=(ring+1)*step*(1+v*.38);points=[]
            for arm in range(arms):
                ang=arm*math.tau/arms+self._phase*(.08+ring*.008);warp=1+math.sin(ang*3+self._phase+ring)*(.10+v*.16);points.extend((cx+math.cos(ang)*radius*warp,cy+math.sin(ang)*radius*warp))
            points.extend(points[:2]);color=self._gradient(ring/12+self._phase*.012);self._canvas.create_line(*points,fill=self._darken(color,.25),width=9,smooth=True);self._canvas.create_line(*points,fill=color,width=1+int(v*4),smooth=True)
        core=8+self.a.bass*28
        for i in range(6):r=core+i*7;self._canvas.create_oval(cx-r,cy-r,cx+r,cy+r,outline=self._gradient(i/6+self._phase*.02),width=2)
    @staticmethod
    def _gradient(t):
        t=t%1.;stops=((0.,(39,232,88)),(.25,(244,230,52)),(.5,(255,145,36)),(.72,(255,61,61)),(1.,(174,62,255)))
        for (a,c1),(b,c2) in zip(stops,stops[1:]):
            if a<=t<=b:q=(t-a)/(b-a);return "#%02x%02x%02x"%tuple(int(x+(y-x)*q) for x,y in zip(c1,c2))
        return "#ae3eff"
    @staticmethod
    def _darken(color,factor):
        factor=max(0.,min(1.,factor));return "#%02x%02x%02x"%tuple(int(int(color[i:i+2],16)*factor) for i in (1,3,5))
