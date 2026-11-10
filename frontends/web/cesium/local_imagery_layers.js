'use strict';
window.ORCLocalImageryLayers = async function(viewer, layers, C, onError=()=>{}) {
  if (!layers.length) return {destroy(){}};
  let disposed=false, lastCheck=0;
  const entries=layers.map(state=>({state,layer:null,pending:false,failed:false,wanted:false}));
  const grid=viewer.imageryLayers.addImageryProvider(new C.GridImageryProvider({color:C.Color.TRANSPARENT,
    glowColor:C.Color.TRANSPARENT,backgroundColor:C.Color.TRANSPARENT,cells:1}),0);
  async function attach(entry,index) {
    if (entry.layer || entry.pending || entry.failed) return;
    entry.pending=true;
    try {
      const state=entry.state;
      const provider=await C.SingleTileImageryProvider.fromUrl(state.url,{
        rectangle:C.Rectangle.fromRadians(state.west_rad,state.south_rad,state.east_rad,state.north_rad),credit:state.attribution});
      if (disposed || viewer.isDestroyed() || !entry.wanted) return;
      entry.layer=viewer.imageryLayers.addImageryProvider(provider,Math.min(index+1,viewer.imageryLayers.length));
      viewer.scene.requestRender();
    } catch(error) {
      entry.failed=true;
      if (!disposed && !viewer.isDestroyed()) onError(error,entry.state);
    } finally { entry.pending=false; }
  }
  function update(force=false) {
    const now=Date.now();
    if (disposed || (!force && now-lastCheck<500)) return;
    lastCheck=now;
    const view=viewer.camera.computeViewRectangle(viewer.scene.globe.ellipsoid);
    entries.forEach((entry,index)=>{
      const s=entry.state;
      const rectangle=C.Rectangle.fromRadians(s.west_rad,s.south_rad,s.east_rad,s.north_rad);
      entry.wanted=index===0 || Boolean(view && C.Rectangle.intersection(view,rectangle));
      if (entry.wanted) attach(entry,index);
      else if (entry.layer) {viewer.imageryLayers.remove(entry.layer,true);entry.layer=null;}
    });
  }
  entries[0].wanted=true;
  await attach(entries[0],0);
  if (viewer.isDestroyed()) return {destroy(){disposed=true;}};
  const remove=viewer.scene.postRender.addEventListener(()=>update());
  update(true);
  return {destroy(){disposed=true;remove();viewer.imageryLayers.remove(grid,true);entries.forEach(entry=>{
    if(entry.layer) viewer.imageryLayers.remove(entry.layer,true);
    entry.layer=null;
  });}};
};
