(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const button=document.getElementById('music-mic-toggle'),status=document.getElementById('music-mic-status'),spectrum=document.getElementById('music-spectrum'),labels=document.getElementById('music-spectrum-labels'),debug=document.getElementById('music-debug');
  const beatCard=document.getElementById('music-beat'),beatStrength=document.getElementById('music-beat-strength'),lightbar=document.getElementById('music-lightbar'),driveLights=document.getElementById('music-drive-lights'),lightStatus=document.getElementById('music-light-status');
  if(!button||!spectrum||!root.MicrophoneMusicAnalyzer)return;
  const analyzer=new root.MicrophoneMusicAnalyzer();
  window.__openRoadMusicAnalyzer=analyzer;
  const bars=Array.from({length:24},()=>{const x=document.createElement('div');x.style.cssText='flex:1;min-width:3px;height:2%;background:linear-gradient(to top,#20c85a 0%,#34d058 34%,#dbe63b 48%,#ffd21c 62%,#ff8a18 78%,#ef3b24 100%);border-radius:4px 4px 0 0;transition:height .025s linear';spectrum.appendChild(x);return x;});
  ['31','41','54','70','92','120','157','205','268','350','457','597','780','1k','1.3k','1.7k','2.2k','2.9k','3.8k','5k','6.5k','8.5k','11k','16k'].forEach((label,i)=>{const x=document.createElement('div');x.textContent=(i%2===0||i===23)?label:'';labels.appendChild(x);});
  root.SpectrumDisplay?.install();

  let beatFlashUntil=0,lastLightSend=0,lastColor='',lastBrightness=-1,smoothBass=0,smoothMid=0,smoothTreble=0,smoothEnergy=0;
  const smooth=(o,n,a=.34,r=.11)=>o+(n-o)*(n>o?a:r),rgbHex=(r,g,b)=>'#'+[r,g,b].map(v=>Math.round(Math.max(0,Math.min(255,v))).toString(16).padStart(2,'0')).join('').toUpperCase();
  const lightColor=(b,m,t)=>{const total=b+m+t+.001;return rgbHex(255*(b+m*.45)/total,255*(m+t*.35)/total,255*(t+m*.18)/total)};
  const post=async payload=>{const r=await fetch('/api/lighting/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok)throw Error(`lighting HTTP ${r.status}`)};
  const drivePhysical=async(color,brightness)=>{if(!driveLights.checked||performance.now()-lastLightSend<120)return;lastLightSend=performance.now();try{if(color!==lastColor){await post({command:'color',value:color});lastColor=color}if(Math.abs(brightness-lastBrightness)>=5){await post({command:'brightness',value:brightness});lastBrightness=brightness}lightStatus.textContent='Driving lighting backend · responsive smoothed output'}catch(e){lightStatus.textContent=`Lighting error: ${e.message}`}};
  driveLights.onchange=async()=>{if(driveLights.checked){try{await post({command:'power',value:true});lightStatus.textContent='Lighting output enabled.'}catch(e){lightStatus.textContent=`Lighting error: ${e.message}`}}else lightStatus.textContent='Preview only.'};

  const drumVisual={
    kick:{previous:0,envelope:0,decay:.78,threshold:.10,boost:1.00},
    snare:{previous:0,envelope:0,decay:.66,threshold:.085,boost:1.00},
    tomHigh:{previous:0,envelope:0,decay:.72,threshold:.09,boost:.95},
    tomLow:{previous:0,envelope:0,decay:.73,threshold:.09,boost:.98},
    cymbal:{previous:0,envelope:0,decay:.88,threshold:.075,boost:.72}
  };
  const updateEnvelope=(name,value)=>{const d=drumVisual[name],rise=Math.max(0,value-d.previous);d.previous=value;if(rise>d.threshold)d.envelope=Math.max(d.envelope,Math.min(1,(rise-d.threshold)*6.2*d.boost+.42));d.envelope*=d.decay;return Math.max(value*.72,d.envelope)};
  const setPunch=(id,value,color,base='')=>{const el=document.getElementById(id);if(!el)return;const scale=1+value*.24;el.style.transform=`${base} scale(${scale})`;el.style.filter=`brightness(${1+value*.24}) saturate(${1+value*.38})`;el.style.boxShadow=`inset 0 0 ${6+value*13}px ${color},0 0 ${8+value*46}px ${color},0 0 ${18+value*38}px ${color}`;};
  const emphasizeDrums=activity=>{
    if(!activity)return;
    const kick=updateEnvelope('kick',activity.kick||0),snare=updateEnvelope('snare',activity.snare||0),tomHigh=updateEnvelope('tomHigh',activity.tomHigh||0),tomLow=updateEnvelope('tomLow',activity.tomLow||0),cymbal=updateEnvelope('cymbal',activity.cymbal||0);
    setPunch('drum-kick',kick,'rgba(255,73,57,.58)','translateX(-50%)');
    setPunch('drum-snare',snare,'rgba(255,198,46,.62)','translateX(-50%)');
    setPunch('drum-tom-high',tomHigh,'rgba(168,76,255,.62)');
    setPunch('drum-tom-low',tomLow,'rgba(40,182,255,.62)');
    for(const [id,dir] of [['drum-cymbal-left',-1],['drum-cymbal-right',1]]){const el=document.getElementById(id);if(!el)continue;el.style.transform=`scaleX(${1+cymbal*.15}) scaleY(${1+cymbal*.08}) rotate(${dir*cymbal*8}deg)`;el.style.filter=`brightness(${1+cymbal*.48}) saturate(${1+cymbal*.30})`;el.style.boxShadow=`0 0 ${12+cymbal*48}px rgba(255,210,45,${.18+cymbal*.62})`;}
  };

  const render=state=>{
    document.getElementById('music-level').value=state.level;document.getElementById('music-bass').value=state.bass;document.getElementById('music-mid').value=state.mid;document.getElementById('music-treble').value=state.treble;document.getElementById('activity-kick').value=state.activity?.kick??0;document.getElementById('activity-bass').value=state.activity?.bass??0;document.getElementById('activity-snare').value=state.activity?.snare??0;document.getElementById('activity-cymbal').value=state.activity?.cymbal??0;
    if(root.SpectrumDisplay)root.SpectrumDisplay.render(state,analyzer,bars);else state.spectrum.forEach((v,i)=>bars[i].style.height=`${Math.max(2,v*100)}%`);
    emphasizeDrums(state.activity);
    smoothBass=smooth(smoothBass,state.bass,.34,.11);smoothMid=smooth(smoothMid,state.mid,.30,.10);smoothTreble=smooth(smoothTreble,state.treble,.27,.09);smoothEnergy=smooth(smoothEnergy,Math.min(1,state.level*.30+state.bass*.42+state.mid*.18+state.treble*.10),.36,.10);const pulse=state.beat?Math.min(.18,.07+state.beatStrength*.11):0,visualEnergy=Math.min(1,smoothEnergy+pulse),color=lightColor(smoothBass,smoothMid,smoothTreble),brightness=Math.round(14+80*visualEnergy);lightbar.style.background=color;lightbar.style.filter=`brightness(${.70+visualEnergy*.82})`;lightbar.style.boxShadow=`0 0 ${8+visualEnergy*13}px ${color},0 0 ${20+visualEnergy*36}px ${color}`;drivePhysical(color,brightness);if(state.beat){beatFlashUntil=performance.now()+70;beatStrength.textContent=`HIT · ${state.beatStrength.toFixed(2)}`}if(performance.now()<beatFlashUntil){beatCard.style.background='#5b2020';beatCard.style.boxShadow='0 0 18px rgba(255,72,32,.45)'}else{beatCard.style.background='#151a20';beatCard.style.boxShadow='none';if(!state.beat)beatStrength.textContent='listening'}debug.textContent=`${state.sampleRateHz} Hz · FFT ${state.fftSize} · flux ${state.beatFlux.toFixed(4)}`;
  };
  button.onclick=async()=>{const enabled=button.dataset.enabled==='1';try{if(enabled){await analyzer.stop();button.dataset.enabled='0';button.textContent='START MICROPHONE';status.textContent='Microphone stopped.';beatStrength.textContent='waiting…'}else{await analyzer.start(render);button.dataset.enabled='1';button.textContent='STOP MICROPHONE';status.textContent='Microphone active. Play some music nearby.'}}catch(error){status.textContent=`Microphone error: ${error.message}`}};
})();
