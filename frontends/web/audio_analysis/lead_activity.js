(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const clamp=v=>Math.max(0,Math.min(1,v));
  let smoothLead=0,peak=1e-6,lastBrightness=0;

  function install(){
    if(document.getElementById('mv-lead-activity'))return true;
    const activity=document.getElementById('mv-activity');
    if(!activity)return false;
    const card=document.createElement('div');
    card.id='mv-lead-activity';
    card.className='card';
    card.style.cssText='padding:18px 20px;min-width:0;overflow:hidden';
    card.innerHTML=`
      <div class="mv-section-title">LEAD ACTIVITY <span class="mv-subtle">experimental melodic-lead heuristic</span></div>
      <div style="display:flex;align-items:center;gap:12px;margin-top:16px;min-width:0">
        <div style="flex:1;min-width:0;height:22px;border-radius:999px;background:#17212c;overflow:hidden;border:1px solid #26384a">
          <div id="mv-lead-fill" style="height:100%;width:0%;border-radius:999px;background:linear-gradient(90deg,#38d6b4,#b06cff,#ff4d90);transition:width .055s linear,filter .055s linear,box-shadow .055s linear"></div>
        </div>
        <b id="mv-lead-status" style="width:58px;text-align:right;color:#8fa0ad">LOW</b>
      </div>
      <p id="mv-lead-debug" style="color:#82909d;font-size:11px;margin:10px 0 0">Looks for sustained bright upper-mid melodic energy; not instrument recognition.</p>`;
    activity.after(card);
    return true;
  }

  function rawBand(analyzer,lo,hi){
    if(!analyzer?.raw||!analyzer?.audioContext)return 0;
    return analyzer.raw(lo,hi)||0;
  }

  function estimate(analyzer,state){
    if(!analyzer?.audioContext||!analyzer?.frequencyData)return 0;
    const body=rawBand(analyzer,650,1800);
    const presence=rawBand(analyzer,1800,4200);
    const air=rawBand(analyzer,4200,7000);
    const low=rawBand(analyzer,80,450);
    const combined=body*.46+presence*.78+air*.18;
    peak=Math.max(combined,peak*.996,1e-6);
    const relative=clamp(combined/peak);
    const brightness=clamp((presence+air*.35)/(body+presence+low*.45+1e-8));
    const brightnessMotion=Math.min(1,Math.abs(brightness-lastBrightness)*5.5);
    lastBrightness=brightness;
    const a=state?.activity||{};
    const percussion=Math.max(a.kick||0,(a.snare||0)*.85,(a.cymbal||0)*.65,(a.tomHigh||0)*.55,(a.tomMid||0)*.55,(a.tomLow||0)*.55);
    const sustain=clamp(relative*.66+brightness*.48);
    const melodicMotion=clamp(brightnessMotion*.32+(state?.mid||0)*.20+(state?.treble||0)*.12);
    const score=clamp(sustain*.72+melodicMotion*.28-percussion*.34);
    smoothLead+= (score-smoothLead)*(score>smoothLead?.24:.075);
    return clamp(smoothLead);
  }

  function render(analyzer,state){
    if(!install())return;
    const value=estimate(analyzer,state),fill=document.getElementById('mv-lead-fill'),status=document.getElementById('mv-lead-status');
    if(fill){fill.style.width=`${value*100}%`;fill.style.filter=`brightness(${.82+value*.55}) saturate(${.9+value*.45})`;fill.style.boxShadow=value>.55?`0 0 ${8+value*18}px rgba(176,108,255,.55)`:'none'}
    if(status){status.textContent=value>.72?'HOT':value>.42?'ACTIVE':'LOW';status.style.color=value>.72?'#ff6aa4':value>.42?'#c18aff':'#8fa0ad'}
  }

  let attempts=0;const boot=()=>{if(install())return;if(attempts++<40)setTimeout(boot,50)};setTimeout(boot,0);
  root.LeadActivity={install,render};
})();
