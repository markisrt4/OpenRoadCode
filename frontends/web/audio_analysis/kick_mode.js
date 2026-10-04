(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  let mode='single',nextLeft=true,lastKick=0,lastOnsetAt=-Infinity;
  const pulse={single:{until:0,duration:115},left:{until:0,duration:115},right:{until:0,duration:115}};
  const ONSET_GAP_MS=48;

  function install(){
    const card=document.getElementById('music-drum-kit');
    const kit=card?.querySelector('.mv-kit');
    if(!card||!kit||document.getElementById('mv-kick-mode'))return !!card;
    const controls=document.createElement('div');
    controls.id='mv-kick-mode';
    controls.style.cssText='display:flex;align-items:center;justify-content:center;gap:8px;margin:14px 0 2px;position:relative;z-index:10;flex-wrap:wrap';
    controls.innerHTML='<span style="font-size:10px;color:#8fa0ad;font-weight:800;margin-right:2px">KICK MODE</span><button type="button" data-kick-mode="single" style="min-height:34px;padding:5px 12px">SINGLE</button><button type="button" data-kick-mode="double" style="min-height:34px;padding:5px 12px">DOUBLE</button>';
    kit.after(controls);
    controls.addEventListener('click',event=>{const button=event.target.closest('[data-kick-mode]');if(button)setMode(button.dataset.kickMode)});
    setMode(mode);
    return true;
  }

  function setMode(next){
    mode=next==='double'?'double':'single';nextLeft=true;lastKick=0;lastOnsetAt=-Infinity;
    pulse.single.until=pulse.left.until=pulse.right.until=0;
    const left=document.getElementById('drum-kick-left'),right=document.getElementById('drum-kick-right');
    if(left){left.style.display='block';left.style.left=mode==='single'?'50%':'';const label=left.querySelector('.mv-drum-label');if(label)label.textContent=mode==='single'?'KICK':'LEFT KICK'}
    if(right)right.style.display=mode==='single'?'none':'block';
    document.querySelectorAll('[data-kick-mode]').forEach(button=>{const active=button.dataset.kickMode===mode;button.classList.toggle('primary',active);button.style.opacity=active?'1':'.62'});
  }

  function detect(kick){
    const now=performance.now(),rise=Math.max(0,kick-lastKick);lastKick=kick;
    if(rise<=.075||kick<=.18||now-lastOnsetAt<=ONSET_GAP_MS)return null;
    let side='single';
    if(mode==='single')pulse.single.until=now+pulse.single.duration;
    else{side=nextLeft?'left':'right';const item=pulse[side];item.until=now+item.duration;nextLeft=!nextLeft}
    lastOnsetAt=now;return side;
  }

  function value(name){const item=pulse[name],remaining=item.until-performance.now();if(remaining<=0)return 0;const t=remaining/item.duration;return Math.sin(Math.PI*Math.min(1,Math.max(0,t)))**.55}

  function render(kick,setPunch){
    install();detect(kick||0);
    if(mode==='single'){setPunch?.('drum-kick-left',value('single'),'rgba(255,73,57,.68)','translateX(-50%)');return}
    setPunch?.('drum-kick-left',value('left'),'rgba(255,73,57,.68)','translateX(-50%)');
    setPunch?.('drum-kick-right',value('right'),'rgba(255,73,57,.68)','translateX(-50%)');
  }

  let attempts=0;const boot=()=>{if(install())return;if(attempts++<50)setTimeout(boot,50)};setTimeout(boot,0);
  root.KickMode={install,setMode,detect,value,render,get mode(){return mode}};
})();
