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
<div class="card">
  <b>Phone Microphone Analyzer <small style="color:#aebac4">EXPERIMENTAL</small></b>
  <p id="music-mic-status">Listen to nearby music with this phone's microphone. No audio is uploaded.</p>
  <button id="music-mic-toggle" class="primary wide" data-enabled="0">START MICROPHONE</button>
</div>
<div id="music-beat" class="card" style="text-align:center;transition:background .04s linear,box-shadow .04s linear"><b style="font-size:28px">BEAT</b><div id="music-beat-strength" style="color:#aebac4;margin-top:5px">waiting…</div></div>
<div class="card">
  <b>Music Light Bar</b>
  <div style="height:105px;display:flex;align-items:center;justify-content:center"><div id="music-lightbar" style="width:92%;height:26px;border-radius:999px;background:#17351f;transition:filter .04s linear,box-shadow .04s linear"></div></div>
  <label style="display:flex;gap:10px;align-items:center"><input id="music-drive-lights" type="checkbox"> Drive lighting backend <small style="color:#aebac4">(whole-zone RGB)</small></label>
  <p id="music-light-status" style="color:#aebac4">Preview only.</p>
</div>
<div class="card">
  <div><b>LEVEL</b><progress id="music-level" max="1" value="0" style="width:100%;height:24px"></progress></div>
  <div><b>BASS</b><progress id="music-bass" max="1" value="0" style="width:100%;height:24px"></progress></div>
  <div><b>MID</b><progress id="music-mid" max="1" value="0" style="width:100%;height:24px"></progress></div>
  <div><b>TREBLE</b><progress id="music-treble" max="1" value="0" style="width:100%;height:24px"></progress></div>
</div>
<div class="card"><b>Spectrum <small style="color:#aebac4">31 Hz → 16 kHz</small></b><div id="music-spectrum" style="height:180px;display:flex;align-items:flex-end;gap:3px;margin-top:16px"></div><p id="music-debug">Waiting for microphone…</p></div>
<script src="/web-assets/audio-analysis/microphone_analyzer.js"></script>
<script>
(() => {
  const button=document.getElementById('music-mic-toggle'),status=document.getElementById('music-mic-status');
  const spectrum=document.getElementById('music-spectrum'),debug=document.getElementById('music-debug');
  const beatCard=document.getElementById('music-beat'),beatStrength=document.getElementById('music-beat-strength');
  const lightbar=document.getElementById('music-lightbar'),driveLights=document.getElementById('music-drive-lights'),lightStatus=document.getElementById('music-light-status');
  const analyzer=new OpenRoadCodeWeb.MicrophoneMusicAnalyzer();
  const bars=Array.from({length:24},()=>{const x=document.createElement('div');x.style.cssText='flex:1;min-width:3px;height:2%;background:linear-gradient(to top,#20c85a 0%,#42d84f 24%,#e6e532 40%,#ffd21c 56%,#ff8a18 74%,#ef3b24 100%);border-radius:4px 4px 0 0;transition:height .025s linear';spectrum.appendChild(x);return x;});
  let beatFlashUntil=0,lastLightSend=0,lastColor='',lastBrightness=-1;
  const rgbHex=(r,g,b)=>'#'+[r,g,b].map(v=>Math.round(Math.max(0,Math.min(255,v))).toString(16).padStart(2,'0')).join('').toUpperCase();
  const lightColor=(state)=>{const total=state.bass+state.mid+state.treble+0.001;return rgbHex(255*(state.bass+state.mid*.45)/total,255*(state.mid+state.treble*.35)/total,255*(state.treble+state.mid*.18)/total);};
  const post=async(payload)=>{const r=await fetch('/api/lighting/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok)throw new Error(`lighting HTTP ${r.status}`);};
  const drivePhysical=async(state,color,brightness)=>{
    if(!driveLights.checked||performance.now()-lastLightSend<110)return;
    lastLightSend=performance.now();
    try{
      if(color!==lastColor){await post({command:'color',value:color});lastColor=color;}
      if(Math.abs(brightness-lastBrightness)>=5){await post({command:'brightness',value:brightness});lastBrightness=brightness;}
      lightStatus.textContent='Driving lighting backend · ~9 updates/sec max';
    }catch(e){lightStatus.textContent=`Lighting error: ${e.message}`;}
  };
  driveLights.onchange=async()=>{if(driveLights.checked){try{await post({command:'power',value:true});lightStatus.textContent='Lighting output enabled.';}catch(e){lightStatus.textContent=`Lighting error: ${e.message}`;}}else lightStatus.textContent='Preview only.';};
  const render=(state)=>{
    document.getElementById('music-level').value=state.level;document.getElementById('music-bass').value=state.bass;document.getElementById('music-mid').value=state.mid;document.getElementById('music-treble').value=state.treble;
    state.spectrum.forEach((value,i)=>bars[i].style.height=`${Math.max(2,value*100)}%`);
    const color=lightColor(state),energy=Math.min(1,state.level*.35+state.bass*.4+state.mid*.15+state.treble*.1),brightness=Math.round(18+82*energy);
    lightbar.style.background=color;lightbar.style.filter=`brightness(${.65+energy*.8})`;lightbar.style.boxShadow=`0 0 ${8+energy*12}px ${color},0 0 ${20+energy*38}px ${color}`;
    drivePhysical(state,color,brightness);
    if(state.beat){beatFlashUntil=performance.now()+90;beatStrength.textContent=`HIT · ${state.beatStrength.toFixed(2)}`;}
    if(performance.now()<beatFlashUntil){beatCard.style.background='#7f1d1d';beatCard.style.boxShadow='0 0 28px rgba(255,72,32,.75)';lightbar.style.filter='brightness(1.75)';}
    else{beatCard.style.background='#151a20';beatCard.style.boxShadow='none';if(!state.beat)beatStrength.textContent='listening';}
    debug.textContent=`${state.sampleRateHz} Hz · FFT ${state.fftSize} · flux ${state.beatFlux.toFixed(4)}`;
  };
  button.onclick=async()=>{const enabled=button.dataset.enabled==='1';try{if(enabled){await analyzer.stop();button.dataset.enabled='0';button.textContent='START MICROPHONE';status.textContent='Microphone stopped.';beatStrength.textContent='waiting…';}else{await analyzer.start(render);button.dataset.enabled='1';button.textContent='STOP MICROPHONE';status.textContent='Microphone active. Play some music nearby.';}}catch(error){status.textContent=`Microphone error: ${error.message}`;}};
})();
</script>
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
        "weather_radio": WebScreen("NOAA Weather Radio", "Weather band", '''<div class="hero-value">162.550<small>MHz</small></div>'''),
        "adsb": WebScreen("ADS-B", "Nearby aircraft", '''<div class="card">No ADS-B source attached</div>'''),
        "airband": WebScreen("Airband", "AM aviation radio", '''<div class="hero-value">118.000<small>MHz AM</small></div>'''),
        "offroad_dashboard": WebScreen("Off-Road", "Phone GPS + orientation", '''<div class="card">Use the existing browser sensor adapters.</div>'''),
        "cabin_lighting": WebScreen("Cabin Lighting", "Shared lighting zone", LIGHTING_HTML),
        "accent_lighting": WebScreen("Accent Lighting", "Shared lighting zone (future independent zone)", LIGHTING_HTML),
        "music_visualizer": WebScreen("Music Visualizer", "Phone microphone FFT experiment", MUSIC_VISUALIZER_HTML),
        "netflix": WebScreen("Netflix", "Browser-native launcher", NETFLIX_HTML),
        "youtube": WebScreen("YouTube", "Browser-native search and video", YOUTUBE_HTML),
    }
