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

MUSIC_VISUALIZER_HTML = '''
<link rel="stylesheet" href="/web-assets/audio-analysis/music_visualizer.css?v=4">
<div class="card"><b>Music Analyzer <small style="color:#aebac4">SHARED DSP</small></b><p id="music-mic-status">Analyze a browser microphone or the Linux host's actual system audio output.</p><button id="music-mic-toggle" class="primary wide" data-enabled="0">START MICROPHONE</button></div>
<div id="music-song-card" class="card"><b>NOW HEARING</b><div id="music-song-provider" style="color:#8fa0ad;font-size:12px;margin-top:3px">Checking song recognition…</div><div id="music-song-title" style="font-size:22px;font-weight:900;margin-top:14px">No song identified</div><div id="music-song-artist" style="color:#c0cad4;margin-top:4px">Waiting for recognition</div><div id="music-song-album" style="color:#81909e;font-size:13px;margin-top:4px">Album metadata will appear here</div><button id="music-song-identify" class="wide" type="button" disabled>IDENTIFY SONG</button><div id="music-song-status" style="color:#8fa0ad;font-size:12px;margin-top:9px">Loading recognition controller state…</div><span id="music-song-state" style="display:none">CHECKING</span></div>
<div id="music-beat" class="card" style="text-align:center"><b style="font-size:28px">PERCUSSION</b><div id="music-beat-strength" style="color:#aebac4;margin-top:5px">Shared analyzer</div></div>
<div class="card"><b>Music Light Bar</b><div style="height:105px;display:flex;align-items:center;justify-content:center"><div id="music-lightbar" style="width:92%;height:26px;border-radius:999px;background:#17351f"></div></div><p id="music-light-status" style="color:#aebac4">Music lighting is controlled by the shared MusicLighting subsystem.</p></div>
<div class="card"><b>Musical Activity</b><div style="margin-top:12px"><b>KICK</b><progress id="activity-kick" max="1" value="0" style="width:100%;height:22px"></progress></div><div><b>BASS</b><progress id="activity-bass" max="1" value="0" style="width:100%;height:22px"></progress></div><div><b>SNARE</b><progress id="activity-snare" max="1" value="0" style="width:100%;height:22px"></progress></div><div><b>CYMBAL</b><progress id="activity-cymbal" max="1" value="0" style="width:100%;height:22px"></progress></div></div>
<div class="card"><div><b>LEVEL</b><progress id="music-level" max="1" value="0" style="width:100%;height:24px"></progress></div><div><b>BASS</b><progress id="music-bass" max="1" value="0" style="width:100%;height:24px"></progress></div><div><b>MID</b><progress id="music-mid" max="1" value="0" style="width:100%;height:24px"></progress></div><div><b>TREBLE</b><progress id="music-treble" max="1" value="0" style="width:100%;height:24px"></progress></div></div>
<div class="card"><b>Spectrum <small style="color:#aebac4">31 Hz → 16 kHz</small></b><div id="music-spectrum" style="height:180px;display:flex;align-items:flex-end;gap:3px;margin-top:16px"></div><div id="music-spectrum-labels" style="display:grid;grid-template-columns:repeat(24,1fr);gap:3px;margin-top:6px;color:#8fa0ad;font-size:9px;line-height:1.1;text-align:center"></div><p id="music-debug">Waiting for audio…</p></div>
<script>(async()=>{const state=document.getElementById('music-song-state'),provider=document.getElementById('music-song-provider'),status=document.getElementById('music-song-status'),button=document.getElementById('music-song-identify');try{const r=await fetch('/api/song-recognition/config'),c=await r.json();if(c.configured){state.textContent='READY';provider.textContent=(c.provider||'song recognition').toUpperCase();status.textContent='Recognition provider ready.';button.disabled=false}else{state.textContent='UNCONFIGURED';provider.textContent='Song recognition controller';status.textContent='No recognition provider configured.';button.disabled=true}}catch(e){state.textContent='OFFLINE';status.textContent=e.message;button.disabled=true}})();</script>
<script src="/web-assets/audio-analysis/microphone_analyzer.js?v=8"></script>
<script src="/web-assets/audio-analysis/spectrum_controls.js?v=7"></script>
<script src="/web-assets/audio-analysis/kick_mode.js?v=3"></script>
<script src="/web-assets/audio-analysis/webgl_music_visualizer.js?v=5"></script>
<script src="/web-assets/audio-analysis/music_visualizer_page.js?v=20"></script>
<script src="/web-assets/audio-analysis/linux_audio_source.js?v=3"></script>
'''

LIGHTING_HTML = '''
<div class="card"><label for="lighting-backend"><b>Lighting device</b></label><select id="lighting-backend" class="search"><option value="emulator">Emulator</option><option value="ble">Physical BLE</option></select><p id="lighting-status">Loading lighting state…</p></div>
<div class="card" style="text-align:center"><canvas id="lighting-wheel" width="280" height="280" style="width:min(78vw,280px);height:min(78vw,280px);touch-action:none"></canvas></div>
<div class="card"><b>Light Bar Preview</b><div id="lighting-preview-stage" style="height:150px;display:flex;align-items:center;justify-content:center;overflow:visible;margin-top:10px"><div id="lighting-swatch" style="width:min(86%,560px);height:30px;border-radius:999px;background:#ffffff;box-shadow:0 0 10px rgba(255,255,255,.8),0 0 28px rgba(255,255,255,.7),0 0 55px rgba(255,255,255,.45);transition:background-color .08s linear,box-shadow .08s linear,opacity .08s linear"></div></div><div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px"><span style="color:#aebac4">Selected color</span><b id="lighting-hex">#FFFFFF</b></div></div>
<div class="card"><div style="display:flex;justify-content:space-between"><b>Brightness</b><span id="lighting-brightness-value">100%</span></div><input id="lighting-brightness" class="wide" type="range" min="0" max="100" value="100"><button id="lighting-power" class="primary wide" data-enabled="0">TURN ON</button></div>
<div class="card"><b>Phone Torch <small style="color:#aebac4">EXPERIMENTAL</small></b><p id="phone-torch-status">Uses this phone's rear camera torch when the browser permits it.</p><button id="phone-torch" class="wide" data-enabled="0">TORCH ON</button></div>
<script src="/web-assets/lighting/lighting.js"></script><script src="/web-assets/lighting/torch.js"></script>
'''


def create_web_screens() -> dict[str, WebScreen]:
    return {
        "vehicle_gauges": WebScreen("Vehicle Gauges", "Mock telemetry mode", '''<div class="gauges"><div class="gauge"><span id="rpm">2450</span><small>RPM</small></div><div class="gauge"><span id="speed">42</span><small>MPH</small></div><div class="gauge"><span id="boost">4.2</span><small>BOOST PSI</small></div><div class="gauge"><span id="throttle">31</span><small>THROTTLE %</small></div></div>'''),
        "weather_overview": WebScreen("Weather", "Frontend provider shell", '''<div class="hero-value">72°<small>F</small></div><div class="card"><b>Current Conditions</b><p>Partly cloudy</p></div>'''),
        "weather_forecast": WebScreen("Forecast", "Demo forecast", '''<div class="forecast"><div><b>MON</b><span>72°</span><small>Partly cloudy</small></div><div><b>TUE</b><span>76°</span><small>Sunny</small></div></div>'''),
        "weather_alerts": WebScreen("Weather Alerts", "Warnings and watches", '''<div class="card"><b>No demo alerts</b></div>'''),
        "fm_radio": WebScreen("FM Radio", "Frontend controls", '''<div class="hero-value">101.1<small>MHz</small></div>'''),
        "scanner_radio": WebScreen("Scanner", "Monitoring controls", '''<div class="card">Scanner idle</div>'''),
        "weather_radio": WebScreen("NOAA Weather Radio", "Weather band", '''<div class="hero-value">162.550<small>MHz AM</small></div>'''),
        "adsb": WebScreen("ADS-B", "Nearby aircraft", '''<div class="card">No ADS-B source attached</div>'''),
        "airband": WebScreen("Airband", "AM aviation radio", '''<div class="hero-value">118.000<small>MHz AM</small></div>'''),
        "offroad_dashboard": WebScreen("Off-Road", "Phone GPS + orientation", '''<div class="card">Use the existing browser sensor adapters.</div>'''),
        "cabin_lighting": WebScreen("Cabin Lighting", "Shared lighting zone", LIGHTING_HTML),
        "accent_lighting": WebScreen("Accent Lighting", "Shared lighting zone (future independent zone)", LIGHTING_HTML),
        "music_visualizer": WebScreen("Music Visualizer", "Browser microphone or Linux PipeWire system audio", MUSIC_VISUALIZER_HTML),
        "netflix": WebScreen("Netflix", "Browser-native launcher", NETFLIX_HTML),
        "youtube": WebScreen("YouTube", "Browser-native search and video", YOUTUBE_HTML),
    }