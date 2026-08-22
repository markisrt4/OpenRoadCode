# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Curses proof-of-concept consuming position and motion ZMQ contracts."""

from __future__ import annotations
import argparse, curses, math, threading
from messaging.contracts.navigation import MOTION_STATE_TOPIC, POSITION_STATE_TOPIC, decode_motion_state, decode_position_state
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber

MPH_PER_MPS=2.2369362920544; FEET_PER_METER=3.2808398950131; FPM_PER_MPS=196.8503937007874; CTRL_X=24

class Latest:
    def __init__(self): self.lock=threading.Lock(); self.position=None; self.motion=None; self.error=None
    def set_position(self,message):
        with self.lock:self.position=message;self.error=None
    def set_motion(self,message):
        with self.lock:self.motion=message;self.error=None
    def set_error(self,topic,error):
        with self.lock:self.error=f"{topic}: {error}"
    def snapshot(self):
        with self.lock:return self.position,self.motion,self.error

def safe(w,r,c,s):
    y,x=w.getmaxyx()
    if 0<=r<y and 0<=c<x-1:
        try:w.addstr(r,c,s[:x-c-1])
        except curses.error:pass

def compass(rad):
    if rad is None:return "--"
    return ("N","NE","E","SE","S","SW","W","NW")[round(math.degrees(rad)/45)%8]

def bar(v,maxv,width=20):
    if v is None:return "["+" "*width+"]"
    n=max(0,min(width,round(abs(v)/maxv*width)));return "["+"#"*n+"-"*(width-n)+"]"

def draw_grid(w,row,col,data):
    if data.latitude_rad is None or data.longitude_rad is None:return
    width,height=31,9;y,x=w.getmaxyx()
    if row+height+2>=y or col+width+2>=x:return
    left,top=col,row+1;right,bottom=left+width-1,top+height-1
    for xx in range(left,right+1):safe(w,top,xx,"-");safe(w,bottom,xx,"-")
    for yy in range(top,bottom+1):safe(w,yy,left,"|");safe(w,yy,right,"|")
    eq=top+(height-1)//2;pm=left+(width-1)//2
    for xx in range(left+1,right):safe(w,eq,xx,"-")
    for yy in range(top+1,bottom):safe(w,yy,pm,"|")
    lat,lon=math.degrees(data.latitude_rad),math.degrees(data.longitude_rad)
    mc=left+round((lon+180)/360*(width-1));mr=top+round((90-lat)/180*(height-1))
    for xx in range(left+1,right):safe(w,mr,xx,"-")
    for yy in range(top+1,bottom):safe(w,yy,mc,"|")
    safe(w,mr,mc,"●");safe(w,bottom+1,left,f"{abs(lat):.4f}°{'N' if lat>=0 else 'S'} {abs(lon):.4f}°{'E' if lon>=0 else 'W'}")

def draw_motion(w,row,col,motion,metric):
    safe(w,row,col,"MOTION  [openroad.navigation.motion]")
    if motion is None:safe(w,row+1,col,"Waiting for motion estimator...");return
    d=motion.data;deg=None if d.heading_rad is None else math.degrees(d.heading_rad)
    safe(w,row+1,col,f"Heading  {compass(d.heading_rad):>2}  {'--' if deg is None else f'{deg:.0f}°'}")
    if metric:
        speed=d.ground_speed_m_s;climb=d.vertical_speed_m_s;st="-- m/s" if speed is None else f"{speed:.1f} m/s";ct="-- m/s" if climb is None else f"{climb:+.2f} m/s";sm,cm=45,8
    else:
        speed=None if d.ground_speed_m_s is None else d.ground_speed_m_s*MPH_PER_MPS;climb=None if d.vertical_speed_m_s is None else d.vertical_speed_m_s*FPM_PER_MPS;st="-- mph" if speed is None else f"{speed:.1f} mph";ct="-- ft/min" if climb is None else f"{climb:+.0f} ft/min";sm,cm=100,1500
    safe(w,row+3,col,f"Speed    {st}");safe(w,row+4,col,bar(speed,sm))
    label="VERTICAL" if climb is None else "CLIMB" if climb>.01 else "DESCENT" if climb<-.01 else "LEVEL";arrow="-" if climb is None or abs(climb)<=.01 else "^" if climb>0 else "v"
    safe(w,row+6,col,f"{label:8} {arrow} {ct}");safe(w,row+7,col,bar(climb,cm));safe(w,row+8,col,f"Motion cached: {'YES' if d.is_cached else 'NO - fresh estimate'}")

def run(w,endpoint,latest):
    curses.curs_set(0);w.timeout(200);metric=False
    while True:
        p,m,e=latest.snapshot();w.erase();safe(w,0,0,"OpenRoadCode Navigation Bus Demo");safe(w,1,0,f"Endpoint: {endpoint}");safe(w,2,0,"Topics: position + motion");safe(w,4,0,f"q/Ctrl+X: quit   u: units   {'METRIC' if metric else 'IMPERIAL'}")
        if e:safe(w,6,0,e)
        elif p is None:safe(w,6,0,"Waiting for position messages...")
        else:
            d=p.data;lat=None if d.latitude_rad is None else math.degrees(d.latitude_rad);lon=None if d.longitude_rad is None else math.degrees(d.longitude_rad);alt=d.altitude_m if metric else None if d.altitude_m is None else d.altitude_m*FEET_PER_METER;unit="m" if metric else "ft"
            for i,(a,b) in enumerate((("Source",p.source),("Latitude","--" if lat is None else f"{lat:.6f}°"),("Longitude","--" if lon is None else f"{lon:.6f}°"),("Altitude","--" if alt is None else f"{alt:.1f} {unit}"),("Cached","YES" if d.is_cached else "NO - fresh fix")),6):safe(w,i,0,f"{a:10}: {b}")
            _,mx=w.getmaxyx();mr,mc=(6,32) if mx>=70 else (13,0);draw_motion(w,mr,mc,m,metric);gr,gc=(16,0) if mx>=70 else (23,0);safe(w,gr,gc,"Global latitude / longitude");draw_grid(w,gr+1,gc,d)
        w.refresh();k=w.getch()
        if k in (ord('q'),ord('Q'),CTRL_X):return
        if k in (ord('u'),ord('U')):metric=not metric

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--endpoint",default="tcp://127.0.0.1:5557");a=ap.parse_args();latest=Latest()
    dispatcher=MessageDispatcher(ZeroMqSubscriber(a.endpoint),error_handler=latest.set_error)
    dispatcher.register(POSITION_STATE_TOPIC,decode_position_state,latest.set_position)
    dispatcher.register(MOTION_STATE_TOPIC,decode_motion_state,latest.set_motion)
    dispatcher.start()
    try:
        curses.wrapper(run,a.endpoint,latest)
    except KeyboardInterrupt:pass
    finally:dispatcher.close()
    return 0
if __name__=="__main__":raise SystemExit(main())
