# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native Tk rendering for OpenRoadCode music analysis."""
from __future__ import annotations

import math
import random
import tkinter as tk
from tkinter import ttk

from controllers.audio_analysis.music_analysis import MusicAnalysisState
from controllers.music_lighting import MusicLightingPatternId, MusicLightingState
from ui.music_analysis import MusicAnalysisRequestHandlerIf, MusicAnalysisStatus, MusicAnalysisUiIf, MusicAnalysisUiState
from ui.music_lighting import MusicLightingRequestHandlerIf, MusicLightingUiIf
from ui.music_visualizer import KickMode, MusicVisualizationMode, MusicVisualizerRequestHandlerIf, MusicVisualizerUiIf, SongRecognitionUiState

_MODE_LABELS={MusicVisualizationMode.SPECTRUM:"Spectrum",MusicVisualizationMode.ORBITING_PLANETS:"Orbiting Planets",MusicVisualizationMode.ELECTRIC_FREEWAY:"Electric Freeway",MusicVisualizationMode.EXPLOSION_FIELD:"Explosion Field",MusicVisualizationMode.STAR_DANCE:"Star Dance",MusicVisualizationMode.ELECTRIC_RINGS:"Electric Rings",MusicVisualizationMode.NEON_RIBBON:"Neon Ribbon",MusicVisualizationMode.KALEIDOSCOPE:"Kaleidoscope"}
_LABEL_MODES={label:mode for mode,label in _MODE_LABELS.items()}
_PATTERN_LABELS={MusicLightingPatternId.SPECTRUM_FLOW:"Spectrum Flow",MusicLightingPatternId.BEAT_PULSE:"Beat Pulse",MusicLightingPatternId.PERCUSSION:"Percussion",MusicLightingPatternId.COLOR_WAVE:"Color Wave",MusicLightingPatternId.AMBIENT:"Ambient"}
_LABEL_PATTERNS={label:pattern for pattern,label in _PATTERN_LABELS.items()}

class MusicVisualizerPanel(tk.Frame,MusicAnalysisUiIf,MusicVisualizerUiIf,MusicLightingUiIf):
    def __init__(self,parent:tk.Misc)->None:
        super().__init__(parent,bg="#0b0d10");self._handler:MusicVisualizerRequestHandlerIf|None=None;self._analysis_handler:MusicAnalysisRequestHandlerIf|None=None;self._lighting_handler:MusicLightingRequestHandlerIf|None=None;self._state:MusicAnalysisState|None=None;self._phase=0.;self._visualization_mode=MusicVisualizationMode.SPECTRUM;self._mode=tk.StringVar(value=_MODE_LABELS[self._visualization_mode]);self._sensitivity=tk.DoubleVar(value=100.);self._lighting=tk.BooleanVar(value=False);self._lighting_pattern=tk.StringVar(value=_PATTERN_LABELS[MusicLightingPatternId.SPECTRUM_FLOW]);self._lighting_intensity=tk.DoubleVar(value=75.);self._kick_mode=tk.StringVar(value=KickMode.SINGLE.value);self._stars=[(random.random(),random.random(),random.uniform(.5,1.5)) for _ in range(70)];self._particles=[];self._pulse={name:0. for name in ("kick","snare","tom_low","tom_mid","tom_high","cymbal")};self._build()
    def set_request_handler(self,handler):self._handler=handler
    def set_music_analysis_request_handler(self,handler):self._analysis_handler=handler
    def set_music_lighting_request_handler(self,handler):self._lighting_handler=handler
    def _build(self):
        controls=tk.Frame(self,bg="#0b0d10");controls.pack(fill="x",padx=8,pady=(4,6));tk.Label(controls,text="VISUALIZER",bg="#0b0d10",fg="white",font=("TkDefaultFont",14,"bold")).pack(side="left");combo=ttk.Combobox(controls,textvariable=self._mode,values=tuple(_MODE_LABELS.values()),state="readonly",width=18);combo.pack(side="right");combo.bind("<<ComboboxSelected>>",self._mode_changed);tk.Button(controls,text="ZEROIZE",command=lambda:self._analysis_handler and self._analysis_handler.request_zeroize(),bg="#18222e",fg="white").pack(side="right",padx=5);self._identify=tk.Button(controls,text="IDENTIFY",command=lambda:self._handler and self._handler.request_song_recognition(),bg="#18222e",fg="white");self._identify.pack(side="right",padx=5);sens=tk.Scale(controls,from_=25,to=200,orient="horizontal",showvalue=False,length=120,bg="#0b0d10",highlightthickness=0,variable=self._sensitivity,command=lambda v:self._analysis_handler and self._analysis_handler.request_sensitivity(float(v)/100.));sens.pack(side="right");tk.Label(controls,text="SENS",bg="#0b0d10",fg="#8fa0ad").pack(side="right")
        options=tk.Frame(self,bg="#0b0d10");options.pack(fill="x",padx=8,pady=(0,5));lighting=tk.Frame(options,bg="#10151b",padx=6,pady=3);lighting.pack(side="left");tk.Checkbutton(lighting,text="MUSIC LIGHTING",variable=self._lighting,command=self._lighting_enabled_changed,bg="#10151b",fg="#aebac4",selectcolor="#18222e",activebackground="#10151b").pack(side="left");pattern=ttk.Combobox(lighting,textvariable=self._lighting_pattern,values=tuple(_PATTERN_LABELS.values()),state="readonly",width=13);pattern.pack(side="left",padx=5);pattern.bind("<<ComboboxSelected>>",self._lighting_pattern_changed);tk.Label(lighting,text="INT",bg="#10151b",fg="#8fa0ad").pack(side="left");tk.Scale(lighting,from_=0,to=100,orient="horizontal",showvalue=False,length=80,bg="#10151b",highlightthickness=0,variable=self._lighting_intensity,command=self._lighting_intensity_changed).pack(side="left");tk.Button(lighting,text="CONFIGURE →",command=self._configure_lighting,bg="#18222e",fg="white").pack(side="left",padx=(5,0));
        for text,value in (("DOUBLE KICK",KickMode.DOUBLE.value),("SINGLE KICK",KickMode.SINGLE.value)):tk.Radiobutton(options,text=text,value=value,variable=self._kick_mode,command=self._kick_changed,bg="#0b0d10",fg="#aebac4",selectcolor="#18222e",activebackground="#0b0d10").pack(side="right")
        self._now=tk.Label(self,text="NOW HEARING  ·  Song recognition unconfigured",anchor="w",bg="#10151b",fg="#b9c8d3",padx=10,pady=5);self._now.pack(fill="x",padx=8,pady=(0,5));self._status=tk.Label(self,text="STOPPED",anchor="w",bg="#0b0d10",fg="#82909d",padx=8);self._status.pack(fill="x");self._canvas=tk.Canvas(self,bg="#030509",highlightthickness=0,height=230);self._canvas.pack(fill="both",expand=True,padx=8);self._drums=tk.Canvas(self,bg="#080c10",highlightthickness=0,height=145);self._drums.pack(fill="x",padx=8,pady=(5,0));meters=tk.Frame(self,bg="#0b0d10");meters.pack(fill="x",padx=8,pady=6);self._meter_labels={}
        for name in ("LEVEL","BASS","MID","TREBLE"):label=tk.Label(meters,text=f"{name}  0%",bg="#0b0d10",fg="#aebac4",font=("TkDefaultFont",9,"bold"));label.pack(side="left",expand=True);self._meter_labels[name.lower()]=label
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
    def _kick_changed(self):
        if self._handler:self._handler.request_kick_mode(KickMode(self._kick_mode.get()))
    def set_analysis_state(self,state):
        self._state=state;self._phase+=.07+state.audio.level*.12
        for name in ("level","bass","mid","treble"):self._meter_labels[name].configure(text=f"{name.upper()}  {int(getattr(state.audio,name)*100):02d}%")
        for name in self._pulse:self._pulse[name]=max(getattr(state.percussion,name),self._pulse[name]*.72)
        self._draw();self._draw_drums()
    def set_analysis_ui_state(self,state:MusicAnalysisUiState)->None:
        self._sensitivity.set(round(state.sensitivity*100));parts=[state.status.value.upper()]
        if state.calibrated:parts.append("ZEROIZED")
        if state.status is MusicAnalysisStatus.ZEROIZING:parts.append("KEEP MUSIC OFF")
        if state.error:parts.append(state.error)
        self._status.configure(text="  ·  ".join(parts))
    def set_song(self,song):
        if song is None:self._now.configure(text="NOW HEARING  ·  No song identified");return
        parts=[song.title,*song.artists];parts+=([song.album] if song.album else []);self._now.configure(text="NOW HEARING  ·  "+" · ".join(parts)+(f"  [{song.provider}]" if song.provider else ""))
    def set_song_recognition_state(self,state):self._identify.configure(state="normal" if state.configured and not state.recognizing else "disabled");self._now.configure(text="NOW HEARING  ·  Listening for song…" if state.recognizing else ("NOW HEARING  ·  Song recognition unconfigured" if not state.configured else f"NOW HEARING  ·  {state.provider or 'Recognizer'} ready · press IDENTIFY"))
    def set_visualization_mode(self,m):self._visualization_mode=m;self._mode.set(_MODE_LABELS[m])
    def _draw(self):
        if not self._state:return
        c=self._canvas;c.delete("all");w,h=max(2,c.winfo_width()),max(2,c.winfo_height());{MusicVisualizationMode.ORBITING_PLANETS:self._draw_planets,MusicVisualizationMode.ELECTRIC_FREEWAY:self._draw_freeway,MusicVisualizationMode.EXPLOSION_FIELD:self._draw_explosion,MusicVisualizationMode.STAR_DANCE:self._draw_stars,MusicVisualizationMode.ELECTRIC_RINGS:self._draw_rings,MusicVisualizationMode.NEON_RIBBON:self._draw_ribbon,MusicVisualizationMode.KALEIDOSCOPE:self._draw_kaleidoscope}.get(self._visualization_mode,self._draw_spectrum)(w,h)
    def _draw_drums(self):
        c=self._drums;c.delete("all");w=max(2,c.winfo_width());h=max(2,c.winfo_height());items=((.15,.54,28,"HIGH TOM","tom_high","#a84cff"),(.34,.54,30,"MID TOM","tom_mid","#38d6b4"),(.54,.54,31,"LOW TOM","tom_low","#28b6ff"),(.73,.62,30,"SNARE","snare","#ffc62e"))
        for xf,yf,r,label,key,color in items:p=self._pulse[key];rr=r*(1+.35*p);x,y=w*xf,h*yf;c.create_text(x,y-r-19,text=label,fill="#aebac4",font=("TkDefaultFont",8,"bold"));c.create_oval(x-rr,y-rr,x+rr,y+rr,fill="#111820",outline=color,width=3+int(p*3))
        kick=self._pulse["kick"];x=w*.89;rr=35*(1+.32*kick);c.create_text(x,26,text="KICK",fill="#aebac4",font=("TkDefaultFont",8,"bold"));c.create_oval(x-rr,38,x+rr,38+rr*2,fill="#111820",outline="#ff6238",width=3);cym=self._pulse["cymbal"];c.create_text(w*.08,8,text="HI-HAT",fill="#aebac4");c.create_line(w*.04,25,w*.12,25,fill="#ffd33d",width=int(3+cym*5));c.create_text(w*.91,8,text="CRASH",fill="#aebac4");c.create_oval(w*.86-28,20,w*.96+8,32,outline="#ffd33d",width=int(2+cym*5))
    @property
    def a(self):return self._state.audio
    def _draw_spectrum(self,w,h):
        vals=self.a.spectrum or (0.,)*24;gap=3;bw=max(2,(w-gap*(len(vals)+1))/len(vals))
        for i,v in enumerate(vals):x=gap+i*(bw+gap);self._canvas.create_rectangle(x,h-8-v*(h-20),x+bw,h-8,fill=self._gradient(i/max(1,len(vals)-1)),outline="")
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
        for i,v in enumerate(self.a.spectrum[::3] or (0,)*8):r=(i+1)*min(w,h)/18+v*28;self._canvas.create_oval(cx-r,cy-r,cx+r,cy+r,outline=self._gradient(i/8+self._phase*.01),width=2+int(v*4))
    def _draw_ribbon(self,w,h):
        vals=self.a.spectrum or (0,)*24;pts=[]
        for i,v in enumerate(vals):pts.extend((i*w/max(1,len(vals)-1),h*.5-math.sin(i*.65+self._phase)*25-v*h*.28))
        if len(pts)>=4:self._canvas.create_line(*pts,fill="#44ddff",width=4,smooth=True)
    def _draw_kaleidoscope(self,w,h):
        cx,cy=w/2,h/2;vals=self.a.spectrum or (0,)*24
        for spoke in range(12):
            a=spoke*math.tau/12+self._phase*.15
            for i,v in enumerate(vals[::3]):r=(i+1)*min(w,h)/20+v*35;x=cx+math.cos(a)*r;y=cy+math.sin(a)*r;self._canvas.create_line(cx,cy,x,y,fill=self._gradient(i/8+spoke/12),width=1+int(v*4))
    @staticmethod
    def _gradient(x):
        x=x%1
        if x<.33:return "#37df78"
        if x<.66:return "#ffd33d"
        return "#ff5b45"
