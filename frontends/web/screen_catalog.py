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


NETFLIX_HTML = '''
<div class="card">
  <b>Netflix</b>
  <p>Open Netflix directly on this device, or search for a title.</p>
  <button id="netflix-open" class="primary wide">OPEN NETFLIX</button>
</div>
<form id="netflix-search-form" class="card">
  <label for="netflix-search"><b>Find a title</b></label>
  <input id="netflix-search" class="search" type="search" placeholder="Movie or show" autocomplete="off">
  <button class="wide" type="submit">SEARCH NETFLIX</button>
</form>
<script src="/web-assets/media/browser_media.js"></script>
'''

YOUTUBE_HTML = '''
<form id="youtube-search-form" class="card">
  <label for="youtube-search"><b>Search YouTube</b></label>
  <input id="youtube-search" class="search" type="search" placeholder="Video, channel, artist…" autocomplete="off">
  <button class="primary wide" type="submit">SEARCH YOUTUBE</button>
</form>
<div class="card">
  <p>Or open YouTube and browse normally on this device.</p>
  <button id="youtube-open" class="wide">OPEN YOUTUBE</button>
</div>
<script src="/web-assets/media/browser_media.js"></script>
'''

LIGHTING_HTML = '''
<div class="card">
  <label for="lighting-backend"><b>Lighting device</b></label>
  <select id="lighting-backend" class="search">
    <option value="emulator">Emulator</option>
    <option value="ble">Physical BLE</option>
  </select>
  <p id="lighting-status">Loading lighting state…</p>
</div>
<div class="card" style="text-align:center">
  <canvas id="lighting-wheel" width="280" height="280" style="width:min(78vw,280px);height:min(78vw,280px);touch-action:none"></canvas>
  <div style="display:flex;justify-content:center;align-items:center;gap:10px;margin-top:10px">
    <span id="lighting-swatch" style="display:inline-block;width:30px;height:30px;border-radius:50%;border:2px solid #fff"></span>
    <b id="lighting-hex">#FFFFFF</b>
  </div>
</div>
<div class="card">
  <div style="display:flex;justify-content:space-between"><b>Brightness</b><span id="lighting-brightness-value">100%</span></div>
  <input id="lighting-brightness" class="wide" type="range" min="0" max="100" value="100">
  <button id="lighting-power" class="primary wide" data-enabled="0">TURN ON</button>
</div>
<script src="/web-assets/lighting/lighting.js"></script>
'''


def create_web_screens() -> dict[str, WebScreen]:
    return {
        "vehicle_gauges": WebScreen("Vehicle Gauges", "Mock telemetry mode", '''<div class="gauges"><div class="gauge"><span id="rpm">2450</span><small>RPM</small></div><div class="gauge"><span id="speed">42</span><small>MPH</small></div><div class="gauge"><span id="boost">4.2</span><small>BOOST PSI</small></div><div class="gauge"><span id="throttle">31</span><small>THROTTLE %</small></div></div><script>setInterval(()=>{const t=Date.now()/1000;rpm.textContent=Math.round(2200+700*Math.sin(t));speed.textContent=Math.round(43+5*Math.sin(t/2));boost.textContent=(4+3*Math.max(0,Math.sin(t))).toFixed(1);throttle.textContent=Math.round(30+15*Math.sin(t/1.7));},250)</script>'''),
        "weather_overview": WebScreen("Weather", "Frontend provider shell", '''<div class="hero-value">72°<small>F</small></div><div class="card"><b>Current Conditions</b><p>Partly cloudy</p></div>'''),
        "weather_forecast": WebScreen("Forecast", "Demo forecast", '''<div class="forecast"><div><b>MON</b><span>72°</span><small>Partly cloudy</small></div><div><b>TUE</b><span>76°</span><small>Sunny</small></div></div>'''),
        "weather_alerts": WebScreen("Weather Alerts", "Warnings and watches", '''<div class="card"><b>No demo alerts</b></div>'''),
        "fm_radio": WebScreen("FM Radio", "Frontend controls", '''<div class="hero-value">101.1<small>MHz</small></div>'''),
        "scanner_radio": WebScreen("Scanner", "Monitoring controls", '''<div class="card">Scanner idle</div>'''),
        "weather_radio": WebScreen("NOAA Weather Radio", "Weather band", '''<div class="hero-value">162.550<small>MHz</small></div>'''),
        "adsb": WebScreen("ADS-B", "Nearby aircraft", '''<div class="card">No ADS-B source attached</div>'''),
        "airband": WebScreen("Airband", "AM aviation radio", '''<div class="hero-value">118.000<small>MHz AM</small></div>'''),
        "offroad_dashboard": WebScreen("Off-Road", "Phone GPS + orientation", '''<div class="stat-grid"><div class="stat"><b id="pitch">--</b><small>PITCH</small></div><div class="stat"><b id="roll">--</b><small>ROLL</small></div><div class="stat"><b id="heading">--</b><small>HEADING</small></div><div class="stat"><b id="speed">--</b><small>GPS MPH</small></div></div><div class="card"><p id="sensor-status">Tap START SENSORS.</p><div id="location">GPS: --</div><button id="start-sensors" class="primary wide">START SENSORS</button></div><script src="/web-assets/sensors/device_orientation.js"></script><script src="/web-assets/sensors/geolocation.js"></script><script>(()=>{const o=new OpenRoadCodeWeb.DeviceOrientationSensorAdapter(),g=new OpenRoadCodeWeb.GeolocationSensorAdapter(),v=(id,x,d=1,s='°')=>document.getElementById(id).textContent=Number.isFinite(x)?`${x.toFixed(d)}${s}`:'--';start_sensors=document.getElementById('start-sensors');start_sensors.onclick=async()=>{if(await o.requestPermission())o.start(x=>{v('pitch',x.pitch);v('roll',x.roll);v('heading',x.heading,0)});g.start(x=>{v('speed',Number.isFinite(x.speed)?x.speed*2.236936:null,1,' mph');location.textContent=`GPS: ${x.latitude.toFixed(6)}, ${x.longitude.toFixed(6)}`});sensor_status.textContent='Sensors active';};})();</script>'''),
        "cabin_lighting": WebScreen("Cabin Lighting", "Emulator or physical BLE", LIGHTING_HTML),
        "accent_lighting": WebScreen("Accent Lighting", "Emulator or physical BLE", LIGHTING_HTML),
        "netflix": WebScreen("Netflix", "Browser-native launcher", NETFLIX_HTML),
        "youtube": WebScreen("YouTube", "Browser-native search and video", YOUTUBE_HTML),
    }
