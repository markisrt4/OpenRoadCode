(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const clamp=v=>Math.max(0,Math.min(1,v));
  let mode='adaptive',sensitivity=1;
  let zeroBaselineDb=null,zeroSamples=null,zeroizeUntil=0;
  const ZEROIZE_MS=1500,ZERO_MARGIN_DB=3.0;

  function install(){
    const spectrum=document.getElementById('music-spectrum');
    if(!spectrum||document.getElementById('spectrum-display-controls'))return false;
    const controls=document.createElement('div');
    controls.id='spectrum-display-controls';
    controls.style.cssText='display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;align-items:end;width:100%;min-width:0;box-sizing:border-box;margin:12px 0 4px';
    controls.innerHTML=`<label style="font-size:12px;color:#c5d0db;min-width:0">DISPLAY MODE<select id="spectrum-mode" class="search" style="margin-top:5px;width:100%;min-width:0;box-sizing:border-box"><option value="adaptive">Adaptive</option><option value="fixed">Fixed</option><option value="hybrid">Hybrid</option></select></label><label style="font-size:12px;color:#c5d0db;min-width:0">SENSITIVITY <span id="spectrum-sensitivity-value">100%</span><input id="spectrum-sensitivity" type="range" min="25" max="200" value="100" step="5" style="width:100%;min-width:0;margin-top:8px"></label>`;
    spectrum.parentNode.insertBefore(controls,spectrum);
    const hint=document.createElement('div');hint.id='spectrum-mode-hint';hint.style.cssText='font-size:11px;color:#82909d;margin:4px 0 8px';controls.after(hint);
    const micButton=document.getElementById('music-mic-toggle');
    if(micButton&&!document.getElementById('spectrum-zeroize')){const zero=document.createElement('button');zero.id='spectrum-zeroize';zero.type='button';zero.className='wide';zero.textContent='ZEROIZE ROOM NOISE';zero.style.cssText='display:none;margin-top:10px;min-height:48px';zero.onclick=startZeroize;micButton.after(zero)}
    document.getElementById('spectrum-mode').onchange=e=>{mode=e.target.value;updateHint()};
    document.getElementById('spectrum-sensitivity').oninput=e=>{sensitivity=Number(e.target.value)/100;document.getElementById('spectrum-sensitivity-value').textContent=e.target.value+'%'};
    updateHint();return true;
  }
  function setCaptureActive(active){const b=document.getElementById('spectrum-zeroize');if(!b)return;b.style.display=active?'block':'none';if(!active){b.disabled=false;b.textContent=zeroBaselineDb?'RE-ZEROIZE ROOM NOISE':'ZEROIZE ROOM NOISE'}}
  function startZeroize(){const a=window.__openRoadMusicAnalyzer,b=document.getElementById('spectrum-zeroize');if(!a?.frequencyData||!a?.audioContext)return;zeroSamples=[];zeroizeUntil=performance.now()+ZEROIZE_MS;if(b){b.disabled=true;b.textContent='ZEROIZING… KEEP MUSIC OFF'}const h=document.getElementById('spectrum-mode-hint');if(h)h.textContent='Listening to ambient room noise for 1.5 seconds…'}
  function finishZeroize(){if(!zeroSamples?.length)return;const bands=zeroSamples[0].length;zeroBaselineDb=Array.from({length:bands},(_,i)=>{const v=zeroSamples.map(r=>r[i]).filter(Number.isFinite).sort((a,b)=>a-b);return v.length?v[Math.min(v.length-1,Math.floor(v.length*.75))]:-100});zeroSamples=null;zeroizeUntil=0;const b=document.getElementById('spectrum-zeroize');if(b){b.disabled=false;b.textContent='RE-ZEROIZE ROOM NOISE'}updateHint()}
  function updateHint(){const h=document.getElementById('spectrum-mode-hint');if(!h)return;const base=mode==='fixed'?'Fixed: stable dB scale; quiet stays quiet.':mode==='hybrid'?'Hybrid: fixed noise floor with limited adaptive lift.':'Adaptive: each band follows its recent peak.';h.textContent=zeroBaselineDb?`${base} Room noise calibration active.`:base}
  function bandDb(data,loHz,hiHz,sr,fftSize){const hz=sr/fftSize,lo=Math.max(1,Math.floor(loHz/hz)),hi=Math.min(data.length,Math.ceil(hiHz/hz));let p=0,n=0;for(let i=lo;i<hi;i++){const db=data[i];if(!Number.isFinite(db))continue;const x=Math.pow(10,db/20);p+=x*x;n++}return n?20*Math.log10(Math.max(Math.sqrt(p/n),1e-8)):-100}
  function spectrumDbValues(a,count){if(!a?.frequencyData||!a?.audioContext)return[];const out=[],min=31.25,max=Math.min(16000,a.audioContext.sampleRate/2),ratio=Math.pow(max/min,1/count);let lo=min;for(let i=0;i<count;i++){const hi=lo*ratio;out.push(bandDb(a.frequencyData,lo,hi,a.audioContext.sampleRate,a.fftSize));lo=hi}return out}
  function fixedValue(db,i){let floor=-82-(sensitivity-1)*18;if(zeroBaselineDb?.[i]!==undefined)floor=Math.max(floor,zeroBaselineDb[i]+ZERO_MARGIN_DB);if(db<=floor)return 0;return clamp((db-floor)/(-24-floor))}
  function zeroizedAdaptive(value,db,i){if(!zeroBaselineDb||zeroBaselineDb[i]===undefined)return clamp(value*sensitivity);const excess=db-zeroBaselineDb[i]-ZERO_MARGIN_DB;return excess<=0?0:clamp(value*sensitivity*clamp(excess/12))}
  function baselineForRange(low,high,a){if(!zeroBaselineDb||!a?.audioContext)return null;const count=zeroBaselineDb.length,min=31.25,max=Math.min(16000,a.audioContext.sampleRate/2),ratio=Math.pow(max/min,1/count),m=[];let lo=min;for(let i=0;i<count;i++){const hi=lo*ratio;if(hi>low&&lo<high)m.push(zeroBaselineDb[i]);lo=hi}return m.length?Math.max(...m):null}
  function rangeGate(low,high,a){if(!zeroBaselineDb||!a?.frequencyData||!a?.audioContext)return 1;const base=baselineForRange(low,high,a);if(base===null)return 1;const cur=bandDb(a.frequencyData,low,high,a.audioContext.sampleRate,a.fftSize),excess=cur-base-ZERO_MARGIN_DB;return excess<=0?0:clamp(excess/10)}
  function filterActivity(activity,a){
    if(!activity)return activity;
    if(zeroizeUntil)return{...activity,kick:0,bass:0,snare:0,cymbal:0,tomHigh:0,tomMid:0,tomLow:0,hit:null};
    if(!zeroBaselineDb)return activity;
    const snareGate=Math.max(rangeGate(160,300,a),rangeGate(1500,5200,a));
    return{...activity,kick:(activity.kick||0)*rangeGate(45,105,a),bass:(activity.bass||0)*rangeGate(55,260,a),snare:(activity.snare||0)*snareGate,cymbal:(activity.cymbal||0)*rangeGate(6000,15000,a),tomHigh:(activity.tomHigh||0)*rangeGate(145,260,a),tomMid:(activity.tomMid||0)*rangeGate(105,195,a),tomLow:(activity.tomLow||0)*rangeGate(70,135,a)};
  }
  function render(state,a,bars){if(!state||!bars?.length)return;const db=spectrumDbValues(a,bars.length);if(db.length&&zeroizeUntil){zeroSamples.push(db.slice());if(performance.now()>=zeroizeUntil)finishZeroize()}if(mode==='adaptive'){state.spectrum.forEach((v,i)=>{if(bars[i])bars[i].style.height=`${Math.max(2,(zeroBaselineDb&&db.length?zeroizedAdaptive(v,db[i],i):clamp(v*sensitivity))*100)}%`});return}if(!db.length)return;for(let i=0;i<bars.length;i++){const fixed=fixedValue(db[i],i);let value=fixed;if(mode==='hybrid'){const adaptive=zeroBaselineDb?zeroizedAdaptive(state.spectrum[i]||0,db[i],i):clamp((state.spectrum[i]||0)*sensitivity);value=clamp(fixed+(fixed<=.02?0:Math.min(.28,Math.max(0,adaptive-fixed)*.45)))}bars[i].style.height=`${Math.max(2,value*100)}%`}}
  root.SpectrumDisplay={install,render,startZeroize,setCaptureActive,filterActivity};
})();