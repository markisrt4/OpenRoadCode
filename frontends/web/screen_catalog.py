# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Browser-native leaf screens used by the standalone web frontend."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class WebScreen:
    title: str
    subtitle: str
    body_html: str

SPOTIFY_HTML='''
<div id="spotify-status" class="notice">Loading Spotify…</div>
<img id="spotify-art" class="spotify-art" alt="Album artwork" hidden>
<div id="spotify-track" class="spotify-track">Nothing playing</div>
<div id="spotify-artist" class="spotify-artist"></div>
<input id="spotify-progress" class="spotify-progress" type="range" min="0" max="1000" value="0">
<div class="spotify-meta"><span id="spotify-position">0:00</span><span id="spotify-duration">0:00</span></div>
<div class="controls"><button onclick="spotifyCommand('previous')">◀◀</button><button id="spotify-play" class="primary" onclick="spotifyToggle()">▶</button><button onclick="spotifyCommand('next')">▶▶</button></div>
<div class="card"><label>Volume <span id="spotify-volume-label">--</span></label><input id="spotify-volume" type="range" min="0" max="100" value="50"></div>
<div class="controls"><button id="lyrics-button" onclick="loadLyrics()">LYRICS</button><button disabled title="Video controller integration comes next">VIDEO</button></div>
<div id="lyrics-card" class="card" hidden><b>Lyrics</b><div id="lyrics" class="lyrics">Loading…</div></div>
<script>
(() => {
 let state=null, seeking=false;
 const fmt=(s)=>{s=Math.max(0,Math.floor(Number(s)||0));return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;};
 window.spotifyCommand=async(command,value=null)=>{
   const r=await fetch('/api/media/spotify/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command,value})});
   const d=await r.json(); if(!r.ok) throw new Error(d.error||'Spotify request failed'); render(d);
 };
 window.spotifyToggle=()=>spotifyCommand(state?.playback==='playing'?'pause':'play');
 function render(s){
   state=s; document.getElementById('spotify-status').textContent=s.status_message||s.availability;
   document.getElementById('spotify-track').textContent=s.title||'Nothing playing'; document.getElementById('spotify-artist').textContent=[s.artist,s.album].filter(Boolean).join(' · ');
   const art=document.getElementById('spotify-art'); if(s.artwork_uri){art.src=s.artwork_uri;art.hidden=false;}else art.hidden=true;
   document.getElementById('spotify-play').textContent=s.playback==='playing'?'❚❚':'▶';
   document.getElementById('spotify-position').textContent=fmt(s.position_s); document.getElementById('spotify-duration').textContent=fmt(s.duration_s);
   if(!seeking){const duration=Number(s.duration_s)||0;document.getElementById('spotify-progress').value=duration?Math.round((Number(s.position_s)||0)/duration*1000):0;}
   if(s.volume_percent!=null){document.getElementById('spotify-volume').value=s.volume_percent;document.getElementById('spotify-volume-label').textContent=`${s.volume_percent}%`;}
 }
 async function refresh(){try{const r=await fetch('/api/media/spotify/state');render(await r.json());}catch(e){document.getElementById('spotify-status').textContent=e.message;}}
 const progress=document.getElementById('spotify-progress'); progress.addEventListener('input',()=>seeking=true); progress.addEventListener('change',()=>{const d=Number(state?.duration_s)||0;seeking=false;if(d)spotifyCommand('seek',d*Number(progress.value)/1000);});
 const volume=document.getElementById('spotify-volume'); volume.addEventListener('change',()=>spotifyCommand('volume',Number(volume.value)));
 window.loadLyrics=async()=>{const card=document.getElementById('lyrics-card'),box=document.getElementById('lyrics');card.hidden=false;box.textContent='Loading…';try{const r=await fetch('/api/media/spotify/lyrics'),d=await r.json();const lines=d.plain_lines?.length?d.plain_lines:(d.synced_lines||[]).map(x=>x.text);box.textContent=lines.length?lines.join('\n'):'No lyrics found.';}catch(e){box.textContent=e.message;}};
 refresh(); setInterval(refresh,3000);
})();
</script>'''

def create_web_screens() -> dict[str, WebScreen]:
    return {
        "vehicle_gauges":WebScreen("Vehicle Gauges","Mock telemetry mode",'''<div class="gauges"><div class="gauge"><span id="rpm">2450</span><small>RPM</small></div><div class="gauge"><span id="speed">42</span><small>MPH</small></div><div class="gauge"><span id="boost">4.2</span><small>BOOST PSI</small></div><div class="gauge"><span id="throttle">31</span><small>THROTTLE %</small></div></div><script>setInterval(()=>{const t=Date.now()/1000;rpm.textContent=Math.round(2200+700*Math.sin(t));speed.textContent=Math.round(43+5*Math.sin(t/2));boost.textContent=(4+3*Math.max(0,Math.sin(t))).toFixed(1);throttle.textContent=Math.round(30+15*Math.sin(t/1.7));},250)</script>'''),
        "weather_overview":WebScreen("Weather","Frontend provider shell",'''<div class="hero-value">72°<small>F</small></div><div class="card"><b>Current Conditions</b><p>Partly cloudy</p></div>'''),
        "weather_forecast":WebScreen("Forecast","Demo forecast",'''<div class="forecast"><div><b>MON</b><span>72°</span><small>Partly cloudy</small></div><div><b>TUE</b><span>76°</span><small>Sunny</small></div></div>'''),
        "weather_alerts":WebScreen("Weather Alerts","Warnings and watches",'''<div class="card"><b>No demo alerts</b></div>'''),
        "fm_radio":WebScreen("FM Radio","Frontend controls",'''<div class="hero-value">101.1<small>MHz</small></div>'''),
        "scanner_radio":WebScreen("Scanner","Monitoring controls",'''<div class="card">Scanner idle</div>'''),
        "weather_radio":WebScreen("NOAA Weather Radio","Weather band",'''<div class="hero-value">162.550<small>MHz</small></div>'''),
        "adsb":WebScreen("ADS-B","Nearby aircraft",'''<div class="card">No ADS-B source attached</div>'''),
        "airband":WebScreen("Airband","AM aviation radio",'''<div class="hero-value">118.000<small>MHz AM</small></div>'''),
        "offroad_dashboard":WebScreen("Off-Road","Phone GPS + orientation",'''<div class="stat-grid"><div class="stat"><b id="pitch">--</b><small>PITCH</small></div><div class="stat"><b id="roll">--</b><small>ROLL</small></div><div class="stat"><b id="heading">--</b><small>HEADING</small></div><div class="stat"><b id="speed">--</b><small>GPS MPH</small></div></div><div class="card"><p id="sensor-status">Tap START SENSORS.</p><div id="location">GPS: --</div><button id="start-sensors" class="primary wide">START SENSORS</button></div><script src="/web-assets/sensors/device_orientation.js"></script><script src="/web-assets/sensors/geolocation.js"></script><script>(()=>{const o=new OpenRoadCodeWeb.DeviceOrientationSensorAdapter(),g=new OpenRoadCodeWeb.GeolocationSensorAdapter(),v=(id,x,d=1,s='°')=>document.getElementById(id).textContent=Number.isFinite(x)?`${x.toFixed(d)}${s}`:'--';start_sensors=document.getElementById('start-sensors');start_sensors.onclick=async()=>{if(await o.requestPermission())o.start(x=>{v('pitch',x.pitch);v('roll',x.roll);v('heading',x.heading,0)});g.start(x=>{v('speed',Number.isFinite(x.speed)?x.speed*2.236936:null,1,' mph');location.textContent=`GPS: ${x.latitude.toFixed(6)}, ${x.longitude.toFixed(6)}`});sensor_status.textContent='Sensors active';};})();</script>'''),
        "cabin_lighting":WebScreen("Cabin Lighting","Frontend controls",'''<div class="card"><input type="range" min="0" max="100"><input type="color"></div>'''),
        "accent_lighting":WebScreen("Accent Lighting","Frontend controls",'''<div class="card"><input type="range" min="0" max="100"><input type="color"></div>'''),
        "spotify":WebScreen("Spotify","OpenRoadCode media controls",SPOTIFY_HTML),
        "netflix":WebScreen("Netflix","Browser integration",'''<div class="card">Netflix launcher</div>'''),
        "youtube":WebScreen("YouTube","Video and search",'''<div class="card"><input class="search" placeholder="Search YouTube"></div>'''),
    }
