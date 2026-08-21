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
    controls.innerHTML=`
      <label style="font-size:12px;color:#c5d0db;min-width:0">DISPLAY MODE
        <select id="spectrum-mode" class="search" style="margin-top:5px;width:100%;min-width:0;box-sizing:border-box">
          <option value="adaptive">Adaptive</option>
          <option value="fixed">Fixed</option>
          <option value="hybrid">Hybrid</option>
        </select>
      </label>
      <label style="font-size:12px;color:#c5d0db;min-width:0">SENSITIVITY <span id="spectrum-sensitivity-value">100%</span>
        <input id="spectrum-sensitivity" type="range" min="25" max="200" value="100" step="5" style="width:100%;min-width:0;margin-top:8px">
      </label>`;
    spectrum.parentNode.insertBefore(controls,spectrum);

    const hint=document.createElement('div');
    hint.id='spectrum-mode-hint';
    hint.style.cssText='font-size:11px;color:#82909d;margin:4px 0 8px';
    controls.after(hint);

    const micButton=document.getElementById('music-mic-toggle');
    if(micButton&&!document.getElementById('spectrum-zeroize')){
      const zero=document.createElement('button');
      zero.id='spectrum-zeroize';
      zero.type='button';
      zero.className='wide';
      zero.textContent='ZEROIZE ROOM NOISE';
      zero.style.cssText='display:none;margin-top:10px;min-height:48px';
      zero.onclick=startZeroize;
      micButton.after(zero);
    }

    document.getElementById('spectrum-mode').onchange=e=>{mode=e.target.value;updateHint()};
    document.getElementById('spectrum-sensitivity').oninput=e=>{sensitivity=Number(e.target.value)/100;document.getElementById('spectrum-sensitivity-value').textContent=e.target.value+'%'};
    updateHint();
    return true;
  }

  function setCaptureActive(active){
    const button=document.getElementById('spectrum-zeroize');
    if(!button)return;
    button.style.display=active?'block':'none';
    if(!active){button.disabled=false;button.textContent=zeroBaselineDb?'RE-ZEROIZE ROOM NOISE':'ZEROIZE ROOM NOISE'}
  }

  function startZeroize(){
    const analyzer=window.__openRoadMusicAnalyzer;
    const button=document.getElementById('spectrum-zeroize');
    if(!analyzer?.frequencyData||!analyzer?.audioContext)return;
    zeroSamples=[];
    zeroizeUntil=performance.now()+ZEROIZE_MS;
    if(button){button.disabled=true;button.textContent='ZEROIZING… KEEP MUSIC OFF'}
    const h=document.getElementById('spectrum-mode-hint');
    if(h)h.textContent='Listening to ambient room noise for 1.5 seconds…';
  }

  function finishZeroize(){
    if(!zeroSamples?.length)return;
    const bands=zeroSamples[0].length;
    zeroBaselineDb=Array.from({length:bands},(_,i)=>{
      const values=zeroSamples.map(row=>row[i]).filter(Number.isFinite).sort((a,b)=>a-b);
      if(!values.length)return -100;
      return values[Math.min(values.length-1,Math.floor(values.length*.75))];
    });
    zeroSamples=null;zeroizeUntil=0;
    const button=document.getElementById('spectrum-zeroize');
    if(button){button.disabled=false;button.textContent='RE-ZEROIZE ROOM NOISE'}
    updateHint();
  }

  function updateHint(){
    const h=document.getElementById('spectrum-mode-hint');
    if(!h)return;
    const base=mode==='fixed'?'Fixed: stable dB scale; quiet stays quiet.' : mode==='hybrid'?'Hybrid: fixed noise floor with limited adaptive lift.' : 'Adaptive: each band follows its recent peak.';
    h.textContent=zeroBaselineDb?`${base} Room noise calibration active.`:base;
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

  function spectrumDbValues(analyzer,count){
    if(!analyzer?.frequencyData||!analyzer?.audioContext)return [];
    const values=[],min=31.25,max=Math.min(16000,analyzer.audioContext.sampleRate/2),ratio=Math.pow(max/min,1/count);
    let lo=min;
    for(let i=0;i<count;i++){
      const hi=lo*ratio;
      values.push(bandDb(analyzer.frequencyData,lo,hi,analyzer.audioContext.sampleRate,analyzer.fftSize));
      lo=hi;
    }
    return values;
  }

  function fixedValue(db,bandIndex){
    let floor=-82-(sensitivity-1)*18;
    if(zeroBaselineDb?.[bandIndex]!==undefined)floor=Math.max(floor,zeroBaselineDb[bandIndex]+ZERO_MARGIN_DB);
    const ceiling=-24;
    if(db<=floor)return 0;
    return clamp((db-floor)/(ceiling-floor));
  }

  function zeroizedAdaptive(value,db,bandIndex){
    if(!zeroBaselineDb||zeroBaselineDb[bandIndex]===undefined)return clamp(value*sensitivity);
    const excess=db-zeroBaselineDb[bandIndex]-ZERO_MARGIN_DB;
    if(excess<=0)return 0;
    return clamp(value*sensitivity*clamp(excess/12.0));
  }

  function baselineForRange(lowHz,highHz,analyzer){
    if(!zeroBaselineDb||!analyzer?.audioContext)return null;
    const count=zeroBaselineDb.length,min=31.25,max=Math.min(16000,analyzer.audioContext.sampleRate/2),ratio=Math.pow(max/min,1/count);
    const matches=[];
    let lo=min;
    for(let i=0;i<count;i++){
      const hi=lo*ratio;
      if(hi>lowHz&&lo<highHz)matches.push(zeroBaselineDb[i]);
      lo=hi;
    }
    return matches.length?Math.max(...matches):null;
  }

  function rangeGate(lowHz,highHz,analyzer){
    if(!zeroBaselineDb||!analyzer?.frequencyData||!analyzer?.audioContext)return 1;
    const baseline=baselineForRange(lowHz,highHz,analyzer);
    if(baseline===null)return 1;
    const current=bandDb(analyzer.frequencyData,lowHz,highHz,analyzer.audioContext.sampleRate,analyzer.fftSize);
    const excess=current-baseline-ZERO_MARGIN_DB;
    if(excess<=0)return 0;
    return clamp(excess/10.0);
  }

  function filterActivity(activity,analyzer){
    if(!activity)return activity;
    if(zeroizeUntil)return {kick:0,bass:0,snare:0,cymbal:0,tomHigh:0,tomLow:0};
    if(!zeroBaselineDb)return activity;
    const snareGate=Math.max(rangeGate(160,300,analyzer),rangeGate(1500,5200,analyzer));
    return {
      kick:(activity.kick||0)*rangeGate(45,105,analyzer),
      bass:(activity.bass||0)*rangeGate(55,260,analyzer),
      snare:(activity.snare||0)*snareGate,
      cymbal:(activity.cymbal||0)*rangeGate(6000,15000,analyzer),
      tomHigh:(activity.tomHigh||0)*rangeGate(120,220,analyzer),
      tomLow:(activity.tomLow||0)*rangeGate(75,145,analyzer)
    };
  }

  function render(state,analyzer,bars){
    if(!state||!bars?.length)return;
    const dbValues=spectrumDbValues(analyzer,bars.length);
    if(dbValues.length&&zeroizeUntil){
      zeroSamples.push(dbValues.slice());
      if(performance.now()>=zeroizeUntil)finishZeroize();
    }

    if(mode==='adaptive'){
      state.spectrum.forEach((v,i)=>{
        if(!bars[i])return;
        const value=zeroBaselineDb&&dbValues.length?zeroizedAdaptive(v,dbValues[i],i):clamp(v*sensitivity);
        bars[i].style.height=`${Math.max(2,value*100)}%`;
      });
      return;
    }
    if(!dbValues.length)return;
    for(let i=0;i<bars.length;i++){
      const fixed=fixedValue(dbValues[i],i);
      let value=fixed;
      if(mode==='hybrid'){
        const adaptive=zeroBaselineDb?zeroizedAdaptive(state.spectrum[i]||0,dbValues[i],i):clamp((state.spectrum[i]||0)*sensitivity);
        const lift=fixed<=.02?0:Math.min(.28,Math.max(0,adaptive-fixed)*.45);
        value=clamp(fixed+lift);
      }
      bars[i].style.height=`${Math.max(2,value*100)}%`;
    }
  }

  root.SpectrumDisplay={install,render,startZeroize,setCaptureActive,filterActivity};
})();
