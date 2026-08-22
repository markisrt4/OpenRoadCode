(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  let activeSource='browser',captureActive=false;
  const visualizerModes=[
    ['tunnel','Frequency Tunnel'],['ribbon','Neon Ribbon'],['field','Spectrum Field'],
    ['plasma','Plasma Bloom'],['kaleidoscope','Kaleidoscope'],['starwarp','Star Warp'],
    ['rings','Electric Rings'],['planets','Dancing Planets'],['stardance','Star Dance'],
    ['instruments','Neon Instruments'],['freeway','Electric Freeway'],['explosions','Explosion Field']
  ];

  function install(){
    const micButton=document.getElementById('music-mic-toggle'),spectrum=document.getElementById('music-spectrum');
    if(!micButton||!spectrum)return false;
    if(!document.getElementById('spectrum-zeroize-controls')){
      const top=document.createElement('div');top.id='spectrum-zeroize-controls';top.className='mv-zeroize-controls';top.innerHTML=`<button id="spectrum-zeroize" type="button" class="wide" disabled>ZEROIZE ROOM NOISE</button><div id="spectrum-analysis-state" class="mv-analysis-state">Start the microphone before zeroizing.</div>`;
      micButton.insertAdjacentElement('afterend',top);
      document.getElementById('spectrum-zeroize').onclick=startZeroize;
    }
    if(!document.getElementById('spectrum-display-controls')){
      const card=spectrum.closest('.card'),controls=document.createElement('div');controls.id='spectrum-display-controls';controls.className='mv-spectrum-controls';
      controls.innerHTML=`<label>SENSITIVITY <span id="spectrum-sensitivity-value">100%</span><input id="spectrum-sensitivity" type="range" min="25" max="200" value="100" step="5"></label><label>VISUALIZER<select id="spectrum-visualizer-mode" class="search">${visualizerModes.map(([value,label])=>`<option value="${value}">${label}</option>`).join('')}</select></label>`;
      card.appendChild(controls);
      document.getElementById('spectrum-sensitivity').oninput=e=>{document.getElementById('spectrum-sensitivity-value').textContent=e.target.value+'%';setSensitivity(Number(e.target.value)/100)};
      document.getElementById('spectrum-visualizer-mode').onchange=e=>setVisualizerMode(e.target.value);
    }
    syncVisualizerSelector();
    return true;
  }

  function setVisualizerMode(value){
    const target=document.getElementById('mv-webgl-mode');
    if(!target)return;
    target.value=value;
    target.dispatchEvent(new Event('change',{bubbles:true}));
    syncVisualizerSelector();
  }

  function syncVisualizerSelector(){
    const selector=document.getElementById('spectrum-visualizer-mode'),target=document.getElementById('mv-webgl-mode');
    if(selector&&target&&selector.value!==target.value)selector.value=target.value;
  }

  function endpoint(action){return `/api/audio-analysis/${activeSource}/${action}`}
  async function fetchState(){const r=await fetch(endpoint('state'),{cache:'no-store'}),j=await r.json();if(!r.ok)throw Error(j.error||`HTTP ${r.status}`);return j}
  function syncState(payload){const ui=payload?.ui||{},state=ui.status||(captureActive?'active':'stopped'),calibrated=ui.calibrated??payload?.calibrated??false,sensitivity=ui.sensitivity??payload?.sensitivity,b=document.getElementById('spectrum-zeroize'),label=document.getElementById('spectrum-analysis-state');if(b){b.disabled=!captureActive||state==='zeroizing';b.style.display=captureActive?'block':'none';b.textContent=state==='zeroizing'?'ZEROIZING… KEEP MUSIC OFF':(calibrated?'RE-ZEROIZE ROOM NOISE':'ZEROIZE ROOM NOISE')}if(Number.isFinite(sensitivity)){const slider=document.getElementById('spectrum-sensitivity'),value=document.getElementById('spectrum-sensitivity-value'),pct=Math.round(sensitivity*100);if(slider&&document.activeElement!==slider)slider.value=String(pct);if(value)value.textContent=pct+'%'}if(label){label.style.display=captureActive?'block':'none';if(state==='zeroizing')label.textContent='ZEROIZING · sampling ambient room/vehicle noise…';else if(state==='error')label.textContent='ANALYSIS ERROR · '+(ui.error||payload?.error||'unknown error');else if(state==='active')label.textContent=calibrated?'ACTIVE · ambient floor applied to spectrum + percussion.':'ACTIVE · not zeroized yet.';else label.textContent=String(state).toUpperCase()}syncVisualizerSelector()}
  async function startZeroize(){if(!captureActive)return;const b=document.getElementById('spectrum-zeroize');try{const r=await fetch(endpoint('zeroize'),{method:'POST'}),j=await r.json();if(!r.ok)throw Error(j.error||`HTTP ${r.status}`);syncState(j);const deadline=Date.now()+5000;while(Date.now()<deadline){await new Promise(resolve=>setTimeout(resolve,120));const state=await fetchState();syncState(state);if(state?.ui?.status==='active'&&(state.ui.calibrated??state.calibrated))return}throw Error('Calibration did not complete; verify PCM frames are arriving')}catch(e){if(b){b.disabled=false;b.textContent='ZEROIZE FAILED'}const label=document.getElementById('spectrum-analysis-state');if(label)label.textContent='ZEROIZE FAILED · '+e.message;console.warn(e)}}
  async function setSensitivity(value){try{const r=await fetch(endpoint('sensitivity'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value})}),j=await r.json();if(!r.ok)throw Error(j.error||`HTTP ${r.status}`);syncState(j)}catch(e){console.warn('Sensitivity update failed',e)}}
  function setCaptureActive(active){captureActive=!!active;if(captureActive)fetchState().then(syncState).catch(()=>{});else syncState({ui:{status:'stopped',calibrated:false}})}
  function setSource(source){activeSource=source==='linux'?'linux':'browser';if(captureActive)fetchState().then(syncState).catch(()=>{})}
  function render(state,bars){const values=state?.audio?.spectrum||state?.spectrum||[];values.forEach((v,i)=>{const bar=bars[i];if(!bar)return;const value=Math.max(0,Math.min(1,v));bar.style.height=`${Math.max(1,value*100)}%`;bar.style.opacity='1';bar.style.borderRadius='4px 4px 0 0'});syncState(state)}
  root.SpectrumDisplay={install,render,startZeroize,setCaptureActive,setSource,syncState,setVisualizerMode};
})();