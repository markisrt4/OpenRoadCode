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
<div class="card"><b>Netflix</b><p>Open Netflix directly on this device, or search for a title.</p><button id="netflix-open" class="primary wide">OPEN NETFLIX</button></div>
<form id="netflix-search-form" class="card"><label for="netflix-search"><b>Find a title</b></label><input id="netflix-search" class="search" type="search" placeholder="Movie or show" autocomplete="off"><button class="wide" type="submit">SEARCH NETFLIX</button></form>
<script src="/web-assets/media/browser_media.js"></script>
'''

YOUTUBE_HTML = '''
<form id="youtube-search-form" class="card"><label for="youtube-search"><b>Search YouTube</b></label><input id="youtube-search" class="search" type="search" placeholder="Video, channel, artist…" autocomplete="off"><button class="primary wide" type="submit">SEARCH YOUTUBE</button></form>
<div class="card"><p>Or open YouTube and browse normally on this device.</p><button id="youtube-open" class="wide">OPEN YOUTUBE</button></div>
<script src="/web-assets/media/browser_media.js"></script>
'''

VEHICLE_GAUGES_HTML = '''
<div class="card"><b>Automotive bus</b><p id="vehicle-obd-status">Waiting for openroad.vehicle.state…</p></div>
<div class="gauges"><div class="gauge"><span id="vehicle-rpm">--</span><small>RPM</small></div><div class="gauge"><span id="vehicle-obd-speed">--</span><small>OBD MPH</small></div><div class="gauge"><span id="vehicle-throttle">--</span><small>THROTTLE %</small></div><div class="gauge"><span id="vehicle-boost">--</span><small>BOOST PSI</small></div><div class="gauge"><span id="vehicle-coolant">--</span><small>COOLANT °F</small></div><div class="gauge"><span id="vehicle-load">--</span><small>ENGINE LOAD %</small></div><div class="gauge"><span id="vehicle-fuel">--</span><small>FUEL %</small></div><div class="gauge"><span id="vehicle-voltage">--</span><small>CONTROL V</small></div></div>
<div class="card"><b>Navigation bus</b><p id="vehicle-sensor-status">Waiting for navigation data, or start phone GPS.</p></div>
<div class="gauges"><div class="gauge"><span id="vehicle-speed">--</span><small>GPS MPH</small></div><div class="gauge"><span id="vehicle-heading">--</span><small>HEADING</small></div><div class="gauge"><span id="vehicle-altitude">--</span><small>ALTITUDE</small></div><div class="gauge"><span id="vehicle-accuracy">--</span><small>GPS ACCURACY</small></div></div>
<div class="card"><b>Phone sensors</b><p>Use this device as a navigation.position producer.</p><button id="start-vehicle-sensors" class="primary wide">START PHONE GPS</button></div>
<script src="/web-assets/sensors/geolocation.js"></script><script src="/web-assets/sensors/vehicle_gauges.js"></script>
'''

MUSIC_VISUALIZER_HTML = '''
<div class="card">
  <button id="music-visualizer-toggle" class="primary wide">START MICROPHONE</button>
  <p id="music-visualizer-status">Start the microphone to feed the shared Python MusicAnalyzer.</p>
</div>
<div id="music-visualizer-anchor"></div>
<div class="card">
  <div style="display:grid;gap:10px">
    <div><small>BASS</small><div style="height:8px;background:#222b34;border-radius:8px"><div id="music-bass" style="height:100%;width:0;background:#45b8ff;border-radius:8px"></div></div></div>
    <div><small>MID</small><div style="height:8px;background:#222b34;border-radius:8px"><div id="music-mid" style="height:100%;width:0;background:#58df7b;border-radius:8px"></div></div></div>
    <div><small>TREBLE</small><div style="height:8px;background:#222b34;border-radius:8px"><div id="music-treble" style="height:100%;width:0;background:#d260ff;border-radius:8px"></div></div></div>
  </div>
</div>
<script src="/web-assets/audio-analysis/browser_pcm_capture.js"></script>
<script src="/web-assets/audio-analysis/webgl_music_visualizer.js"></script>
<script src="/web-assets/audio-analysis/music_visualizer.js"></script>
'''


def create_web_screens() -> dict[str, WebScreen]:
    return {
        "vehicle_gauges": WebScreen("Vehicle Gauges", "Navigation + automotive bus", VEHICLE_GAUGES_HTML),
        "weather_overview": WebScreen("Weather", "Frontend provider shell", '''<div class="hero-value">72°<small>F</small></div><div class="card"><b>Current Conditions</b><p>Partly cloudy</p></div>'''),
        "weather_forecast": WebScreen("Forecast", "Demo forecast", '''<div class="forecast"><div><b>MON</b><span>72°</span><small>Partly cloudy</small></div><div><b>TUE</b><span>76°</span><small>Sunny</small></div></div>'''),
        "weather_alerts": WebScreen("Weather Alerts", "Warnings and watches", '''<div class="card"><b>No demo alerts</b></div>'''),
        "fm_radio": WebScreen("FM Radio", "Frontend controls", '''<div class="hero-value">101.1<small>MHz</small></div>'''),
        "scanner_radio": WebScreen("Scanner", "Monitoring controls", '''<div class="card">Scanner idle</div>'''),
        "weather_radio": WebScreen("NOAA Weather Radio", "Weather band", '''<div class="hero-value">162.550<small>MHz</small></div>'''),
        "adsb": WebScreen("ADS-B", "Nearby aircraft", '''<div class="card">No ADS-B source attached</div>'''),
        "airband": WebScreen("Airband", "AM aviation radio", '''<div class="hero-value">118.000<small>MHz AM</small></div>'''),
        "offroad_dashboard": WebScreen("Off-Road", "Phone GPS + orientation", '''<div class="stat-grid"><div class="stat"><b id="pitch">--</b><small>PITCH</small></div><div class="stat"><b id="roll">--</b><small>ROLL</small></div><div class="stat"><b id="heading">--</b><small>HEADING</small></div><div class="stat"><b id="speed">--</b><small>GPS MPH</small></div></div><div class="card"><p id="sensor-status">Tap START SENSORS.</p><div id="location">GPS: --</div><button id="start-sensors" class="primary wide">START SENSORS</button></div><script src="/web-assets/sensors/device_orientation.js"></script><script src="/web-assets/sensors/geolocation.js"></script><script>(()=>{const o=new OpenRoadCodeWeb.DeviceOrientationSensorAdapter(),g=new OpenRoadCodeWeb.GeolocationSensorAdapter(),v=(id,x,d=1,s='°')=>document.getElementById(id).textContent=Number.isFinite(x)?`${x.toFixed(d)}${s}`:'--';start_sensors=document.getElementById('start-sensors');start_sensors.onclick=async()=>{if(await o.requestPermission())o.start(x=>{v('pitch',x.pitch);v('roll',x.roll);v('heading',x.heading,0)});g.start(x=>{v('speed',Number.isFinite(x.speed)?x.speed*2.236936:null,1,' mph');location.textContent=`GPS: ${x.latitude.toFixed(6)}, ${x.longitude.toFixed(6)}`});sensor_status.textContent='Sensors active';};})();</script>'''),
        "cabin_lighting": WebScreen("Cabin Lighting", "Frontend controls", '''<div class="card"><input type="range" min="0" max="100"><input type="color"></div>'''),
        "accent_lighting": WebScreen("Accent Lighting", "Frontend controls", '''<div class="card"><input type="range" min="0" max="100"><input type="color"></div>'''),
        "netflix": WebScreen("Netflix", "Browser-native launcher", NETFLIX_HTML),
        "youtube": WebScreen("YouTube", "Browser-native search and video", YOUTUBE_HTML),
        "music_visualizer": WebScreen("Music Visualizer", "Browser audio + shared analyzer", MUSIC_VISUALIZER_HTML),
    }
