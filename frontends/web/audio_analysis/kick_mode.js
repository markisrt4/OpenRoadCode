(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  let mode='double',nextLeft=true,lastKick=0,lastOnsetAt=-Infinity;
  const pulse={single:{until:0,duration:115},left:{until:0,duration:115},right:{until:0,duration:115}};
  const ONSET_GAP_MS=48;

  function install(){
    const card=document.getElementById('music-drum-kit');
    const kit=card?.querySelector('.mv-kit');
    if(!card||!kit||document.getElementById('mv-kick-mode'))return !!card;
    const controls=document.createElement('div');
    controls.id='mv-kick-mode';
    controls.style.cssText='display:flex;align-items:center;justify-content:flex-end;gap:8px;margin:-24px 0 8px;position:relative;z-index:10';
    controls.innerHTML='<span style="font-size:10px;color:#8fa0ad;font-weight:800">KICK MODE</span><button type="button" data-kick-mode="single" style="min-height:30px;padding:4px 10px">SINGLE</button><button type="button" data-kick-mode="double" style="min-height:30px;padding:4px 10px">DOUBLE</button>';
    card.querySelector('.mv-section-title')?.after(controls);
    controls.addEventListener('click',e=>{const b=e.target.closest('[data-kick-mode]');if(!b)return;setMode(b.dataset.kickMode)});
    setMode(mode);
    return true;
  }

  function setMode(next){
    mode=next==='single'?'single':'double';nextLeft=true;lastKick=0;
    const left=document.getElementById('drum-kick-left'),right=document.getElementById('drum-kick-right');
    if(left){left.style.display='block';left.style.left=mode==='single'?'58%':'';left.querySelector('.mv-drum-label').textContent=mode==='single'?'KICK':'LEFT KICK'}
    if(right)right.style.display=mode==='single'?'none':'block';
    document.querySelectorAll('[data-kick-mode]').forEach(b=>{const active=b.dataset.kickMode===mode;b.classList.toggle('primary',active);b.style.opacity=active?'1':'.62'});
  }

  function detect(kick){
    const now=performance.now(),rise=Math.max(0,kick-lastKick);lastKick=kick;
    if(rise<=.075||kick<=.18||now-lastOnsetAt<=ONSET_GAP_MS)return;
    if(mode==='single')pulse.single.until=now+pulse.single.duration;
    else{const p=nextLeft?pulse.left:pulse.right;p.until=now+p.duration;nextLeft=!nextLeft}
    lastOnsetAt=now;
  }

  function value(p){const remaining=p.until-performance.now();if(remaining<=0)return 0;const t=remaining/p.duration;return Math.sin(Math.PI*Math.min(1,Math.max(0,t)))**.55}

  function render(kick,setPunch){
    install();detect(kick||0);
    if(mode==='single'){
      setPunch('drum-kick-left',value(pulse.single),'rgba(255,73,57,.68)','translateX(-50%)');
      return;
    }
    setPunch('drum-kick-left',value(pulse.left),'rgba(255,73,57,.68)','translateX(-50%)');
    setPunch('drum-kick-right',value(pulse.right),'rgba(255,73,57,.68)','translateX(-50%)');
  }

  let attempts=0;const boot=()=>{if(install())return;if(attempts++<50)setTimeout(boot,50)};setTimeout(boot,0);
  root.KickMode={install,setMode,render,get mode(){return mode}};
})();
