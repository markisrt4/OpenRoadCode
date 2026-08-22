(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  let activeSource='browser';

  function install(){
    const spectrum=document.getElementById('music-spectrum');
    if(!spectrum||document.getElementById('spectrum-display-controls'))return false;
    const controls=document.createElement('div');
    controls.id='spectrum-display-controls';
    controls.style.cssText='display:grid;grid-template-columns:minmax(0,1fr);gap:12px;width:100%;min-width:0;box-sizing:border-box;margin:12px 0 4px';
    controls.innerHTML=`<label style="font-size:12px;color:#c5d0db;min-width:0">SENSITIVITY <span id="spectrum-sensitivity-value">100%</span><input id="spectrum-sensitivity" type="range" min="25" max="200" value="100" step="5" style="width:100%;min-width:0;margin-top:8px"></label>`;
    spectrum.parentNode.insertBefore(controls,spectrum);
    const hint=document.createElement('div');hint.id='spectrum-mode-hint';hint.style.cssText='font-size:11px;color:#82909d;margin:4px 0 8px';hint.textContent='Analysis, noise calibration, and percussion detection run in the shared Python MusicAnalyzer.';controls.after(hint);
    const micButton=document.getElementById('music-mic-toggle');
    if(micButton&&!document.getElementById('spectrum-zeroize')){const zero=document.createElement('button');zero.id='spectrum-zeroize';zero.type='button';zero.className='wide';zero.textContent='ZEROIZE ROOM NOISE';zero.style.cssText='display:none;margin-top:10px;min-height:48px';zero.onclick=startZeroize;micButton.after(zero)}
    document.getElementById('spectrum-sensitivity').oninput=e=>{const value=Number(e.target.value)/100;document.getElementById('spectrum-sensitivity-value').textContent=e.target.value+'%';setSensitivity(value)};
    return true;
  }
  function endpoint(action){return `/api/audio-analysis/${activeSource}/${action}`}
  async function startZeroize(){const b=document.getElementById('spectrum-zeroize');if(b){b.disabled=true;b.textContent='ZEROIZING… KEEP MUSIC OFF'}try{const r=await fetch(endpoint('zeroize'),{method:'POST'});const j=await r.json();if(!r.ok)throw Error(j.error||`HTTP ${r.status}`);syncState(j)}catch(e){if(b){b.disabled=false;b.textContent='ZEROIZE FAILED'}console.warn(e)}}
  async function setSensitivity(value){try{const r=await fetch(endpoint('sensitivity'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value})});const j=await r.json();if(!r.ok)throw Error(j.error||`HTTP ${r.status}`);syncState(j)}catch(e){console.warn('Sensitivity update failed',e)}}
  function syncState(payload){const ui=payload?.ui||{},state=ui.status||'';const calibrated=ui.calibrated??payload?.calibrated??false;const sensitivity=ui.sensitivity??payload?.sensitivity;const b=document.getElementById('spectrum-zeroize');if(b){if(state==='zeroizing'){b.disabled=true;b.textContent='ZEROIZING… KEEP MUSIC OFF'}else{b.disabled=false;b.textContent=calibrated?'RE-ZEROIZE ROOM NOISE':'ZEROIZE ROOM NOISE'}}if(Number.isFinite(sensitivity)){const slider=document.getElementById('spectrum-sensitivity'),label=document.getElementById('spectrum-sensitivity-value'),pct=Math.round(sensitivity*100);if(slider&&document.activeElement!==slider)slider.value=String(pct);if(label)label.textContent=pct+'%'}}
  function setCaptureActive(active){const b=document.getElementById('spectrum-zeroize');if(b)b.style.display=active?'block':'none'}
  function setSource(source){activeSource=source==='linux'?'linux':'browser'}
  function render(state,bars){const spectrum=state?.audio?.spectrum||state?.spectrum||[];spectrum.forEach((v,i)=>{if(bars[i])bars[i].style.height=`${Math.max(2,Math.max(0,Math.min(1,v))*100)}%`});syncState(state)}
  root.SpectrumDisplay={install,render,startZeroize,setCaptureActive,setSource,syncState};
})();