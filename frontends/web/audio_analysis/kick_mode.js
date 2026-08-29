(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  let mode='single';
  let nextLeft=true;
  let lastKick=0;
  let lastOnsetAt=-Infinity;
  const pulse={
    single:{until:0,duration:115},
    left:{until:0,duration:115},
    right:{until:0,duration:115},
  };
  const ONSET_GAP_MS=48;

  function setMode(next){
    mode=next==='double'?'double':'single';
    nextLeft=true;
    lastKick=0;
    lastOnsetAt=-Infinity;
    pulse.single.until=pulse.left.until=pulse.right.until=0;
  }

  function detect(kick){
    const now=performance.now();
    const rise=Math.max(0,kick-lastKick);
    lastKick=kick;
    if(rise<=0.075||kick<=0.18||now-lastOnsetAt<=ONSET_GAP_MS)return null;
    let side='single';
    if(mode==='single'){
      pulse.single.until=now+pulse.single.duration;
    }else{
      side=nextLeft?'left':'right';
      pulse[side].until=now+pulse[side].duration;
      nextLeft=!nextLeft;
    }
    lastOnsetAt=now;
    return side;
  }

  function value(name){
    const item=pulse[name];
    const remaining=item.until-performance.now();
    if(remaining<=0)return 0;
    const t=Math.min(1,Math.max(0,remaining/item.duration));
    return Math.sin(Math.PI*t)**0.55;
  }

  root.KickMode={
    setMode,
    detect,
    value,
    render(kick,callback){
      detect(kick||0);
      if(mode==='single')callback?.('single',value('single'));
      else{
        callback?.('left',value('left'));
        callback?.('right',value('right'));
      }
    },
    get mode(){return mode;},
  };
})();
