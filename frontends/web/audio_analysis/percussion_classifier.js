(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const clamp=v=>Math.max(0,Math.min(1,v));
  const previous={sub:0,kickBody:0,low:0,mid:0,high:0,attack:0};
  const peaks={sub:1e-6,kickBody:1e-6,low:1e-6,mid:1e-6,high:1e-6,attack:1e-6};

  const band=(a,lo,hi)=>a?.raw?(a.raw(lo,hi)||0):0;
  function feature(a,name,lo,hi){
    const raw=band(a,lo,hi);
    peaks[name]=Math.max(raw,peaks[name]*.995,1e-6);
    const n=clamp(raw/peaks[name]);
    const rise=Math.max(0,n-previous[name]);
    previous[name]=n;
    return {n,rise};
  }

  function classify(a,activity){
    if(!a?.audioContext||!a?.frequencyData||!activity)return activity;
    const sub=feature(a,'sub',38,78),kickBody=feature(a,'kickBody',78,118),low=feature(a,'low',90,145),mid=feature(a,'mid',115,200),high=feature(a,'high',165,280),attack=feature(a,'attack',2200,5200);
    const transient=Math.max(sub.rise,kickBody.rise,low.rise,mid.rise,high.rise);
    if(transient<.035)return {...activity,tomMid:(activity.tomMid||0)*.35};

    let kick= sub.n*.70 + kickBody.n*.48 + sub.rise*1.05 + kickBody.rise*.72 + attack.rise*.12 - mid.n*.18 - high.n*.12;
    let tomLow= low.n*.62 + low.rise*.95 + mid.n*.18 - sub.n*.50 - sub.rise*.42;
    let tomMid= mid.n*.66 + mid.rise*1.02 + high.n*.14 - sub.n*.58 - sub.rise*.50 - kickBody.n*.16;
    let tomHigh= high.n*.70 + high.rise*1.04 + attack.rise*.10 - sub.n*.46 - low.n*.14;
    kick=Math.max(0,kick);tomLow=Math.max(0,tomLow);tomMid=Math.max(0,tomMid);tomHigh=Math.max(0,tomHigh);

    const scores=[['kick',kick],['tomLow',tomLow],['tomMid',tomMid],['tomHigh',tomHigh]].sort((x,y)=>y[1]-x[1]);
    const best=Math.max(scores[0][1],1e-6),second=scores[1][1];
    const out={...activity,kick:0,tomLow:0,tomMid:0,tomHigh:0};
    out[scores[0][0]]=clamp(best);
    if(second>best*.78)out[scores[1][0]]=clamp(second*.55);
    return out;
  }

  root.PercussionClassifier={classify};
})();
