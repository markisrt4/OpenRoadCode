# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Browser map confirmation for the installer without a web-framework dependency."""

import math
from ui.navigation.map_ui_if import GeoPoint


HTML = r'''<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Confirm destination</title><style>
body{margin:0;background:#101820;color:#edf5fb;font:16px sans-serif}header,footer{padding:14px}
h2{margin:0 0 8px;font-size:20px}p{margin:6px 0;color:#b8c8d4}#map{height:58vh;position:relative;overflow:hidden;touch-action:none;background:#263540}
#tiles{position:absolute;inset:0}#tiles img{position:absolute;width:256px;height:256px;user-select:none;pointer-events:none}
#pin{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);color:#ff526e;font-size:42px;pointer-events:none;text-shadow:0 2px 3px #000}
button{background:#243746;color:#fff;border:0;padding:12px 16px;font-size:16px;border-radius:6px;margin:4px}
button.primary{background:#167cba}a{color:#7bcaed}.zoom{position:absolute;right:8px;top:8px;z-index:2;display:flex;flex-direction:column}
</style><header><h2 id="title"></h2><p id="address"></p><p>Check the location. Drag to pan; tap the map to move the pin. Address matches may be approximate.</p></header>
<div id="map"><div id="tiles"></div><div id="pin">●</div><div class="zoom"><button id="plus">+</button><button id="minus">−</button></div></div>
<footer><button class="primary" id="use" disabled>Use this location</button><button id="cancel">Cancel</button><p id="status"></p>
<small>Map © <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap contributors</a> · Online US address lookup: US Census Bureau</small></footer>
<script>const data=__DATA__;
document.querySelector('#title').textContent='Confirm '+data.label;
document.querySelector('#address').textContent=data.address;
let lat=data.lat,lon=data.lon,centerLat=lat,centerLon=lon,z=17,start=null,version=0;
const map=document.querySelector('#map'),tiles=document.querySelector('#tiles'),pin=document.querySelector('#pin');
function xy(a,b){a=Math.max(-85.0511,Math.min(85.0511,a));let n=256*2**z,s=Math.sin(a*Math.PI/180);return[(b+180)/360*n,(.5-Math.log((1+s)/(1-s))/(4*Math.PI))*n]}
function ll(x,y){let n=256*2**z;return[Math.atan(Math.sinh(Math.PI*(1-2*y/n)))*180/Math.PI,((x/n*360-180)+540)%360-180]}
function draw(){let v=++version;document.querySelector('#use').disabled=true;document.querySelector('#status').textContent='Loading map…';let c=xy(centerLat,centerLon),w=map.clientWidth,h=map.clientHeight,left=c[0]-w/2,top=c[1]-h/2;tiles.replaceChildren();
for(let x=Math.floor(left/256);x<=Math.floor((left+w)/256);x++)for(let y=Math.floor(top/256);y<=Math.floor((top+h)/256);y++){if(y<0||y>=2**z)continue;let img=document.createElement('img');img.src=`https://tile.openstreetmap.org/${z}/${(x+2**z)%2**z}/${y}.png`;img.onload=()=>{if(v===version && x===Math.floor(c[0]/256) && y===Math.floor(c[1]/256)){document.querySelector('#use').disabled=false;document.querySelector('#status').textContent='Confirm the pin is at your destination.'}};img.onerror=()=>{if(v===version)document.querySelector('#status').textContent='Some map tiles could not load. Check internet access.'};img.style.left=(x*256-left)+'px';img.style.top=(y*256-top)+'px';tiles.append(img)}
let p=xy(lat,lon);pin.style.left=(p[0]-left)+'px';pin.style.top=(p[1]-top)+'px'}
map.onpointerdown=e=>{if(e.target.closest('button'))return;map.setPointerCapture(e.pointerId);start={x:e.clientX,y:e.clientY,c:xy(centerLat,centerLon)}};
map.onpointerup=e=>{if(!start)return;let dx=e.clientX-start.x,dy=e.clientY-start.y;if(Math.hypot(dx,dy)<8){let r=map.getBoundingClientRect(),c=xy(centerLat,centerLon);[lat,lon]=ll(c[0]+e.clientX-r.left-map.clientWidth/2,c[1]+e.clientY-r.top-map.clientHeight/2)}else{[centerLat,centerLon]=ll(start.c[0]-dx,start.c[1]-dy)}start=null;draw()};
map.onpointercancel=()=>start=null;
document.querySelector('#plus').onclick=()=>{z=Math.min(19,z+1);draw()};document.querySelector('#minus').onclick=()=>{z=Math.max(3,z-1);draw()};window.onresize=draw;
async function finish(cancel){let r=await fetch('/confirm?token='+data.token,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cancel,lat,lon})});if(r.ok){document.querySelector('#status').textContent='Return to the terminal to finish setup.';document.querySelector('#use').disabled=true;document.querySelector('#cancel').disabled=true}}
document.querySelector('#use').onclick=()=>finish(false);document.querySelector('#cancel').onclick=()=>finish(true);draw();</script></html>'''


def validate_position(payload):
    """Return a finite, bounded position from the map's degree values."""
    lat, lon = float(payload["lat"]), float(payload["lon"])
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Invalid position")
    return GeoPoint(math.radians(lat), math.radians(lon))
