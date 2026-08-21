(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const clamp=v=>Math.max(0,Math.min(1,v));
  let smoothLead=0,baseline=1e-6,lastBrightness=0;

  function install(){
    if(document.getElementById('mv-lead-activity'))return true;
    const activity=document.getElementById('mv-activity');if(!activity)return false;
    const card=document.createElement('div');card.id='mv-lead-activity';card.className='card';card.style.cssText='padding:18px 20px;min-width:0;overflow:hidden';
    card.innerHTML=`<div class="mv-section-title">LEAD ACTIVITY <span class="mv-subtle">relative melodic-lead prominence</span></div><div style="display:flex;align-items:center;gap:12px;margin-top:16px;min-width:0"><div style="flex:1;min-width:0;height:22px;border-radius:999px;background:#17212c;overflow:hidden;border:1px solid #26384a"><div id="mv-lead-fill" style="height:100%;width:0%;border-radius:999px;background:linear-gradient(90deg,#38d6b4,#b06cff,#ff4d90);transition:width .05s linear,filter .05s linear,box-shadow .05s linear"></div></div><b id="mv-lead-status" style="width:58px;text-align:right;color:#8fa0ad">LOW</b></div><p style="color:#82909d;font-size:11px;margin:10px 0 0">Relative prominence, not guitar recognition. Vocals/synths can still fool it.</p>`;
    activity.after(card);return true;
  }
  const raw=(a,lo,hi)=>a?.raw&&a?.audioContext?(a.raw(lo,hi)||0):0;
  function estimate(a,state){
    if(!a?.audioContext||!a?.frequencyData)return 0;
    const body=raw(a,700,1800),presence=raw(a,1800,4200),air=raw(a,4200,7000),low=raw(a,80,500);
    const leadEnergy=body*.42+presence*.92+air*.24;
    baseline=baseline*.995+leadEnergy*.005;
    baseline=Math.max(baseline,1e-6);
    const prominence=clamp((leadEnergy/(baseline*1.15)-.65)/1.15);
    const brightness=clamp((presence+air*.42)/(body+presence+low*.32+1e-8));
    const motion=clamp(Math.abs(brightness-lastBrightness)*7.5);lastBrightness=brightness;
    const act=state?.activity||{};
    const percussion=Math.max((act.kick||0)*.55,(act.snare||0)*.48,(act.cymbal||0)*.30,(act.tomHigh||0)*.35,(act.tomMid||0)*.35,(act.tomLow||0)*.35);
    const rawScore=clamp(prominence*.72+brightness*.28+motion*.16-percussion*.18);
    smoothLead+=(rawScore-smoothLead)*(rawScore>smoothLead?.34:.09);
    return clamp(smoothLead);
  }
  function render(a,state){if(!install())return;const v=estimate(a,state),fill=document.getElementById('mv-lead-fill'),status=document.getElementById('mv-lead-status');if(fill){fill.style.width=`${v*100}%`;fill.style.filter=`brightness(${.85+v*.65}) saturate(${.95+v*.55})`;fill.style.boxShadow=v>.5?`0 0 ${10+v*20}px rgba(176,108,255,.6)`:'none'}if(status){status.textContent=v>.68?'HOT':v>.34?'ACTIVE':'LOW';status.style.color=v>.68?'#ff6aa4':v>.34?'#c18aff':'#8fa0ad'}}
  let attempts=0;const boot=()=>{if(install())return;if(attempts++<40)setTimeout(boot,50)};setTimeout(boot,0);root.LeadActivity={install,render};
})();
