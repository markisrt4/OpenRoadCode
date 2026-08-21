(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const clamp=v=>Math.max(0,Math.min(1,v));
  let mode='adaptive',sensitivity=1;

  function install(){
    const spectrum=document.getElementById('music-spectrum');
    if(!spectrum||document.getElementById('spectrum-display-controls'))return false;
    const controls=document.createElement('div');
    controls.id='spectrum-display-controls';
    controls.style.cssText='display:grid;grid-template-columns:minmax(140px,1fr) 1fr;gap:12px;align-items:end;margin:12px 0 4px';
    controls.innerHTML=`
      <label style="font-size:12px;color:#c5d0db">DISPLAY MODE
        <select id="spectrum-mode" class="search" style="margin-top:5px">
          <option value="adaptive">Adaptive</option>
          <option value="fixed">Fixed</option>
          <option value="hybrid">Hybrid</option>
        </select>
      </label>
      <label style="font-size:12px;color:#c5d0db">SENSITIVITY <span id="spectrum-sensitivity-value">100%</span>
        <input id="spectrum-sensitivity" type="range" min="25" max="200" value="100" step="5" style="width:100%;margin-top:8px">
      </label>`;
    spectrum.parentNode.insertBefore(controls,spectrum);
    const hint=document.createElement('div');
    hint.id='spectrum-mode-hint';
    hint.style.cssText='font-size:11px;color:#82909d;margin:4px 0 8px';
    controls.after(hint);
    document.getElementById('spectrum-mode').onchange=e=>{mode=e.target.value;updateHint()};
    document.getElementById('spectrum-sensitivity').oninput=e=>{sensitivity=Number(e.target.value)/100;document.getElementById('spectrum-sensitivity-value').textContent=e.target.value+'%'};
    updateHint();
    return true;
  }

  function updateHint(){
    const h=document.getElementById('spectrum-mode-hint');
    if(!h)return;
    h.textContent=mode==='fixed'?'Fixed: stable dB scale; quiet stays quiet.' : mode==='hybrid'?'Hybrid: fixed noise floor with limited adaptive lift.' : 'Adaptive: each band follows its recent peak.';
  }

  function bandDb(data,loHz,hiHz,sr,fftSize){
    const hz=sr/fftSize,lo=Math.max(1,Math.floor(loHz/hz)),hi=Math.min(data.length,Math.ceil(hiHz/hz));
    let power=0,n=0;
    for(let i=lo;i<hi;i++){
      const db=data[i];
      if(!Number.isFinite(db))continue;
      const x=Math.pow(10,db/20);power+=x*x;n++;
    }
    if(!n)return -100;
    return 20*Math.log10(Math.max(Math.sqrt(power/n),1e-8));
  }

  function fixedValue(db){
    const floor=-82-(sensitivity-1)*18;
    const ceiling=-24;
    return clamp((db-floor)/(ceiling-floor));
  }

  function render(state,analyzer,bars){
    if(!state||!bars?.length)return;
    if(mode==='adaptive'){
      state.spectrum.forEach((v,i)=>{if(bars[i])bars[i].style.height=`${Math.max(2,clamp(v*sensitivity)*100)}%`});
      return;
    }
    if(!analyzer?.frequencyData||!analyzer?.audioContext)return;
    const min=31.25,max=Math.min(16000,analyzer.audioContext.sampleRate/2),ratio=Math.pow(max/min,bars.length?1/bars.length:1);
    let lo=min;
    for(let i=0;i<bars.length;i++){
      const hi=lo*ratio;
      const db=bandDb(analyzer.frequencyData,lo,hi,analyzer.audioContext.sampleRate,analyzer.fftSize);
      const fixed=fixedValue(db);
      let value=fixed;
      if(mode==='hybrid'){
        const adaptive=clamp((state.spectrum[i]||0)*sensitivity);
        const lift=fixed<=.02?0:Math.min(.28,Math.max(0,adaptive-fixed)*.45);
        value=clamp(fixed+lift);
      }
      bars[i].style.height=`${Math.max(2,value*100)}%`;
      lo=hi;
    }
  }

  root.SpectrumDisplay={install,render};
})();
