(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const pulse={snare:0,tomHigh:0,tomMid:0,tomLow:0,cymbal:0};
  const previous={snare:0,tomHigh:0,tomMid:0,tomLow:0,cymbal:0};
  const lastHit={snare:-Infinity,tomHigh:-Infinity,tomMid:-Infinity,tomLow:-Infinity,cymbal:-Infinity};
  const thresholds={snare:.16,tomHigh:.14,tomMid:.14,tomLow:.15,cymbal:.17};
  const rises={snare:.055,tomHigh:.045,tomMid:.045,tomLow:.05,cymbal:.055};
  const refractoryMs={snare:72,tomHigh:78,tomMid:82,tomLow:88,cymbal:64};
  const decay={snare:.62,tomHigh:.64,tomMid:.65,tomLow:.67,cymbal:.60};

  function install(){
    if(document.getElementById('music-drum-kit'))return true;
    const anchor=document.getElementById('music-visualizer-anchor');if(!anchor)return false;
    const card=document.createElement('div');card.id='music-drum-kit';card.className='card mv-drum-card';
    const meter=(name,id)=>`<div><div class="mv-meter-name">${name}</div><div id="${id}" class="mv-segments">${'<i class="mv-segment"></i>'.repeat(8)}</div></div>`;
    card.innerHTML=`<div class="mv-section-heading"><div class="mv-section-title">PERCUSSION <span class="mv-subtle">Drum Kit</span></div><button id="mv-toggle-drums" class="mv-compact-button" type="button">HIDE DRUMS</button></div><div id="mv-kit-wrap"><div class="mv-kit"><div id="drum-cymbal-left" class="mv-cymbal mv-cymbal-left"></div><span class="mv-kit-name mv-name-hihat">HI-HAT</span><div id="drum-cymbal-right" class="mv-cymbal mv-cymbal-right"></div><span class="mv-kit-name mv-name-crash">CRASH</span><span class="mv-drum-label mv-label-tom-high">HIGH TOM</span><div id="drum-tom-high" class="mv-drum mv-tom mv-tom-high"></div><span class="mv-drum-label mv-label-tom-mid">MID TOM</span><div id="drum-tom-mid" class="mv-drum mv-tom mv-tom-mid"></div><span class="mv-drum-label mv-label-tom-low">LOW TOM</span><div id="drum-tom-low" class="mv-drum mv-tom mv-tom-low"></div><span class="mv-drum-label mv-label-snare">SNARE</span><div id="drum-snare" class="mv-drum mv-snare"></div><div id="drum-kick-left" class="mv-drum mv-kick mv-kick-left"><span class="mv-drum-label">LEFT KICK</span></div><div id="drum-kick-right" class="mv-drum mv-kick mv-kick-right"><span class="mv-drum-label">RIGHT KICK</span></div></div></div><div class="mv-activity-inline"><div class="mv-activity-title">PERCUSSION ACTIVITY</div><div class="mv-meter-grid-six">${meter('KICK','mv-seg-kick')}${meter('SNARE','mv-seg-snare')}${meter('TOM L','mv-seg-tomLow')}${meter('TOM M','mv-seg-tomMid')}${meter('TOM H','mv-seg-tomHigh')}${meter('CYMBAL','mv-seg-cymbal')}</div></div>`;
    anchor.after(card);card.querySelector('#mv-toggle-drums').onclick=()=>{const wrap=card.querySelector('#mv-kit-wrap'),hidden=wrap.hidden;wrap.hidden=!hidden;card.querySelector('#mv-toggle-drums').textContent=hidden?'HIDE DRUMS':'SHOW DRUMS'};
    root.KickMode?.install();return true;
  }

  function onset(name,value){
    const now=performance.now(),rise=Math.max(0,value-previous[name]);
    previous[name]=value;
    const hit=value>=thresholds[name]&&rise>=rises[name]&&now-lastHit[name]>=refractoryMs[name];
    if(hit){lastHit[name]=now;pulse[name]=Math.max(pulse[name],Math.min(1,.58+value*.62))}
    else pulse[name]*=decay[name];
    return pulse[name];
  }

  function punch(id,value,color,base=''){const el=document.getElementById(id);if(!el)return;el.style.transform=`${base} scale(${1+value*.28})`;el.style.filter=`brightness(${1+value*.42})`;el.style.boxShadow=value>.02?`0 0 ${8+value*28}px ${color}`:'none'}
  function meter(id,value,color){const el=document.getElementById(id);if(!el)return;const on=Math.round(Math.max(0,Math.min(1,value))*el.children.length);[...el.children].forEach((x,i)=>{x.style.background=i<on?color:'#16202a';x.style.opacity=i<on?1:.35})}
  function render(p={}){
    install();
    const v={kick:p.kick||0,snare:p.snare||0,tomLow:p.tom_low??p.tomLow??0,tomMid:p.tom_mid??p.tomMid??0,tomHigh:p.tom_high??p.tomHigh??0,cymbal:p.cymbal||0};
    root.KickMode?.render(v.kick,punch);
    const hits={snare:onset('snare',v.snare),tomHigh:onset('tomHigh',v.tomHigh),tomMid:onset('tomMid',v.tomMid),tomLow:onset('tomLow',v.tomLow),cymbal:onset('cymbal',v.cymbal)};
    punch('drum-snare',hits.snare,'rgba(255,198,46,.68)','translateX(-50%)');
    punch('drum-tom-high',hits.tomHigh,'rgba(168,76,255,.68)');
    punch('drum-tom-mid',hits.tomMid,'rgba(56,214,180,.68)');
    punch('drum-tom-low',hits.tomLow,'rgba(40,182,255,.68)');
    for(const id of ['drum-cymbal-left','drum-cymbal-right'])punch(id,hits.cymbal,'rgba(255,205,55,.55)');
    meter('mv-seg-kick',v.kick,'#ff4939');meter('mv-seg-snare',v.snare,'#ff9c27');meter('mv-seg-tomLow',v.tomLow,'#ffe138');meter('mv-seg-tomMid',v.tomMid,'#50df58');meter('mv-seg-tomHigh',v.tomHigh,'#32c7f2');meter('mv-seg-cymbal',v.cymbal,'#c858ff')
  }
  root.PercussionDisplay={install,render};install();
})();
