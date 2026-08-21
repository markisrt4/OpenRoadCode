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
<div class="card"><b>Music Light Bar</b><div style="height:105px;display:flex;align-items:center;justify-content:center"><div id="music-lightbar" style="width:92%;height:26px;border-radius:999px;background:#17351f;transition:background .085s linear,filter .085s linear,box-shadow .085s linear"></div></div><label style="display:flex;gap:10px;align-items:center"><input id="music-drive-lights" type="checkbox"> Drive lighting backend <small style="color:#aebac4">(whole-zone RGB)</small></label><p id="music-light-status" style="color:#aebac4">Preview only.</p></div>
<div class="card"><b>Musical Activity <small style="color:#aebac4">heuristic DSP</small></b><div style="margin-top:12px"><b>KICK</b><progress id="activity-kick" max="1" value="0" style="width:100%;height:22px"></progress></div><div><b>BASS</b><progress id="activity-bass" max="1" value="0" style="width:100%;height:22px"></progress></div><div><b>SNARE</b><progress id="activity-snare" max="1" value="0" style="width:100%;height:22px"></progress></div><div><b>CYMBAL</b><progress id="activity-cymbal" max="1" value="0" style="width:100%;height:22px"></progress></div><p style="color:#aebac4">Broad activity estimates, not instrument recognition.</p></div>
<div class="card"><div><b>LEVEL</b><progress id="music-level" max="1" value="0" style="width:100%;height:24px"></progress></div><div><b>BASS</b><progress id="music-bass" max="1" value="0" style="width:100%;height:24px"></progress></div><div><b>MID</b><progress id="music-mid" max="1" value="0" style="width:100%;height:24px"></progress></div><div><b>TREBLE</b><progress id="music-treble" max="1" value="0" style="width:100%;height:24px"></progress></div></div>
<div class="card"><b>Spectrum <small style="color:#aebac4">31 Hz → 16 kHz</small></b><div id="music-spectrum" style="height:180px;display:flex;align-items:flex-end;gap:3px;margin-top:16px"></div><div id="music-spectrum-labels" style="display:grid;grid-template-columns:repeat(24,1fr);gap:3px;margin-top:6px;color:#8fa0ad;font-size:9px;line-height:1.1;text-align:center"></div><p id="music-debug">Waiting for microphone…</p></div>
<script src="/web-assets/audio-analysis/pitch_tracker.js?v=1"></script>
<script src="/web-assets/audio-analysis/microphone_analyzer.js?v=5"></script>
<script>
(() => {
  const button=document.getElementById('music-mic-toggle'),status=document.getElementById('music-mic-status'),spectrum=document.getElementById('music-spectrum'),labels=document.getElementById('music-spectrum-labels'),debug=document.getElementById('music-debug');
  const beatCard=document.getElementById('music-beat'),beatStrength=document.getElementById('music-beat-strength'),lightbar=document.getElementById('music-lightbar'),driveLights=document.getElementById('music-drive-lights'),lightStatus=document.getElementById('music-light-status');
  const analyzer=new OpenRoadCodeWeb.MicrophoneMusicAnalyzer(),pitchTracker=new OpenRoadCodeWeb.HarmonicPitchTracker();
  const bars=Array.from({length:24},()=>{const x=document.createElement('div');x.style.cssText='flex:1;min-width:3px;height:2%;background:linear-gradient(to top,#20c85a 0%,#34d058 34%,#dbe63b 48%,#ffd21c 62%,#ff8a18 78%,#ef3b24 100%);border-radius:4px 4px 0 0;transition:height .025s linear';spectrum.appendChild(x);return x;});
  ['31','41','54','70','92','120','157','205','268','350','457','597','780','1k','1.3k','1.7k','2.2k','2.9k','3.8k','5k','6.5k','8.5k','11k','16k'].forEach((label,i)=>{const x=document.createElement('div');x.textContent=(i%2===0||i===23)?label:'';labels.appendChild(x);});
  let beatFlashUntil=0,lastLightSend=0,lastColor='',lastBrightness=-1,smoothBass=0,smoothMid=0,smoothTreble=0,smoothEnergy=0;
  const smooth=(o,n,a=.34,r=.11)=>o+(n-o)*(n>o?a:r),rgbHex=(r,g,b)=>'#'+[r,g,b].map(v=>Math.round(Math.max(0,Math.min(255,v))).toString(16).padStart(2,'0')).join('').toUpperCase();
  const lightColor=(b,m,t)=>{const total=b+m+t+.001;return rgbHex(255*(b+m*.45)/total,255*(m+t*.35)/total,255*(t+m*.18)/total)};
  const post=async payload=>{const r=await fetch('/api/lighting/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok)throw Error(`lighting HTTP ${r.status}`)};
  const drivePhysical=async(color,brightness)=>{if(!driveLights.checked||performance.now()-lastLightSend<120)return;lastLightSend=performance.now();try{if(color!==lastColor){await post({command:'color',value:color});lastColor=color}if(Math.abs(brightness-lastBrightness)>=5){await post({command:'brightness',value:brightness});lastBrightness=brightness}lightStatus.textContent='Driving lighting backend · responsive smoothed output'}catch(e){lightStatus.textContent=`Lighting error: ${e.message}`}};
  driveLights.onchange=async()=>{if(driveLights.checked){try{await post({command:'power',value:true});lightStatus.textContent='Lighting output enabled.'}catch(e){lightStatus.textContent=`Lighting error: ${e.message}`}}else lightStatus.textContent='Preview only.'};
  const render=state=>{document.getElementById('music-level').value=state.level;document.getElementById('music-bass').value=state.bass;document.getElementById('music-mid').value=state.mid;document.getElementById('music-treble').value=state.treble;document.getElementById('activity-kick').value=state.activity?.kick??0;document.getElementById('activity-bass').value=state.activity?.bass??0;document.getElementById('activity-snare').value=state.activity?.snare??0;document.getElementById('activity-cymbal').value=state.activity?.cymbal??0;state.spectrum.forEach((v,i)=>bars[i].style.height=`${Math.max(2,v*100)}%`);
    if(state.frequencyData){const pitch=pitchTracker.track(state.frequencyData,state.sampleRateHz,state.fftSize);OpenRoadCodeWeb.PitchVisualizer?.render(pitch)}
    smoothBass=smooth(smoothBass,state.bass,.34,.11);smoothMid=smooth(smoothMid,state.mid,.30,.10);smoothTreble=smooth(smoothTreble,state.treble,.27,.09);smoothEnergy=smooth(smoothEnergy,Math.min(1,state.level*.30+state.bass*.42+state.mid*.18+state.treble*.10),.36,.10);const pulse=state.beat?Math.min(.18,.07+state.beatStrength*.11):0,visualEnergy=Math.min(1,smoothEnergy+pulse),color=lightColor(smoothBass,smoothMid,smoothTreble),brightness=Math.round(14+80*visualEnergy);lightbar.style.background=color;lightbar.style.filter=`brightness(${.70+visualEnergy*.82})`;lightbar.style.boxShadow=`0 0 ${8+visualEnergy*13}px ${color},0 0 ${20+visualEnergy*36}px ${color}`;drivePhysical(color,brightness);if(state.beat){beatFlashUntil=performance.now()+70;beatStrength.textContent=`HIT · ${state.beatStrength.toFixed(2)}`}if(performance.now()<beatFlashUntil){beatCard.style.background='#5b2020';beatCard.style.boxShadow='0 0 18px rgba(255,72,32,.45)'}else{beatCard.style.background='#151a20';beatCard.style.boxShadow='none';if(!state.beat)beatStrength.textContent='listening'}debug.textContent=`${state.sampleRateHz} Hz · FFT ${state.fftSize} · flux ${state.beatFlux.toFixed(4)}`};
  button.onclick=async()=>{const enabled=button.dataset.enabled==='1';try{if(enabled){await analyzer.stop();button.dataset.enabled='0';button.textContent='START MICROPHONE';status.textContent='Microphone stopped.';beatStrength.textContent='waiting…'}else{await analyzer.start(render);button.dataset.enabled='1';button.textContent='STOP MICROPHONE';status.textContent='Microphone active. Play some music nearby.'}}catch(error){status.textContent=`Microphone error: ${error.message}`}};
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
        "netflix": WebScreen("Netflix", "Browser launcher", NETFLIX_HTML),
        "youtube": WebScreen("YouTube", "Browser launcher", YOUTUBE_HTML),
        "music-visualizer": WebScreen("Music Visualizer", "Phone microphone FFT experiment", MUSIC_VISUALIZER_HTML),
        "lighting": WebScreen("Lighting", "Color + brightness control", LIGHTING_HTML),
    }
