(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const clamp=v=>Math.max(0,Math.min(1,v));
  const names=['sub','kickBody','low','mid','high','snareBody','crack','air'];
  const peaks=Object.fromEntries(names.map(n=>[n,1e-6]));
  const previous=Object.fromEntries(names.map(n=>[n,0]));
  const history=[];
  let lastEventAt=-Infinity,eventId=0;
  const REFRACTORY_MS=42;
  const band=(a,lo,hi)=>a?.raw?(a.raw(lo,hi)||0):0;
  function normalized(a,name,lo,hi){const raw=band(a,lo,hi);peaks[name]=Math.max(raw,peaks[name]*.996,1e-6);return clamp(raw/peaks[name])}
  function frame(a){const f={sub:normalized(a,'sub',38,78),kickBody:normalized(a,'kickBody',78,118),low:normalized(a,'low',90,145),mid:normalized(a,'mid',115,200),high:normalized(a,'high',165,280),snareBody:normalized(a,'snareBody',180,420),crack:normalized(a,'crack',1500,5200),air:normalized(a,'air',6000,12000)};f.rise={};for(const n of names){f.rise[n]=Math.max(0,f[n]-previous[n]);previous[n]=f[n]}return f}
  const avg=(frames,key)=>frames.reduce((s,f)=>s+f[key],0)/Math.max(1,frames.length),maxRise=(frames,key)=>Math.max(...frames.map(f=>f.rise[key]),0);
  function classify(a,activity){
    if(!a?.audioContext||!a?.frequencyData||!activity)return activity;
    const f=frame(a);history.push(f);if(history.length>4)history.shift();
    const gatedEnergy=Math.max(activity.kick||0,activity.snare||0,activity.tomHigh||0,activity.tomMid||0,activity.tomLow||0,activity.cymbal||0),lowFlux=Math.max(f.rise.sub,f.rise.kickBody,f.rise.low,f.rise.mid,f.rise.high),broadbandFlux=Math.max(f.rise.snareBody,f.rise.crack,f.rise.air),onset=Math.max(lowFlux,broadbandFlux*.86),now=performance.now();
    const quiet={...activity,kick:0,snare:0,tomLow:0,tomMid:0,tomHigh:0,hit:null,secondaryHit:null};
    if(gatedEnergy<.07||onset<.045||now-lastEventAt<REFRACTORY_MS)return quiet;
    const recent=history.slice(-3),sub=avg(recent,'sub'),kb=avg(recent,'kickBody'),lo=avg(recent,'low'),mid=avg(recent,'mid'),hi=avg(recent,'high'),sb=avg(recent,'snareBody'),cr=avg(recent,'crack');
    const rSub=maxRise(recent,'sub'),rKb=maxRise(recent,'kickBody'),rLo=maxRise(recent,'low'),rMid=maxRise(recent,'mid'),rHi=maxRise(recent,'high'),rSb=maxRise(recent,'snareBody'),rCr=maxRise(recent,'crack'),rAir=maxRise(recent,'air');
    let kick=sub*.78+kb*.58+rSub*1.15+rKb*.82+rCr*.08-mid*.28-hi*.14;
    let tomLow=lo*.76+rLo*1.10+mid*.18-sub*.52-rSub*.38-kb*.14;
    let tomMid=mid*.74+rMid*1.08+hi*.14-sub*.48-rSub*.35-kb*.20-rKb*.10;
    let tomHigh=hi*.82+rHi*1.12+sb*.20+rCr*.10-sub*.38-lo*.14;
    let snare=sb*.56+cr*.82+rSb*.74+rCr*1.16+rAir*.32-sub*.18-kb*.08;
    kick=Math.max(0,kick);tomLow=Math.max(0,tomLow);tomMid=Math.max(0,tomMid);tomHigh=Math.max(0,tomHigh);snare=Math.max(0,snare);
    const scores=[['kick',kick],['snare',snare],['tomLow',tomLow],['tomMid',tomMid],['tomHigh',tomHigh]].sort((x,y)=>y[1]-x[1]),best=scores[0][1],second=scores[1][1];if(best<.18)return quiet;
    lastEventAt=now;const out={...quiet};out[scores[0][0]]=clamp(.48+best*.52);out.hit={id:++eventId,type:scores[0][0],strength:clamp(best)};
    if(second>.18&&second>best*.58){out[scores[1][0]]=clamp(.30+second*.34);out.secondaryHit={id:++eventId,type:scores[1][0],strength:clamp(second*.72)}}
    return out;
  }
  root.PercussionClassifier={classify};
})();