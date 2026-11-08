'use strict';
window.ORCLocalImageryLayers = async function(viewer, layers, C, onError=()=>{}) {
  if (!layers.length) return {destroy(){}};
  const maximumActive=6;
  let disposed=false, lastCheck=0;
  const entries=layers.map(state=>({state,layer:null,pending:false,failed:false,wanted:false}));
  const grid=await window.ORCReferenceGlobeLayer(viewer,C);
  if (!grid) return {destroy(){disposed=true;}};
  async function attach(entry,index) {
    if (entry.layer || entry.pending || entry.failed ||
        entries.filter(item=>item.pending).length>=maximumActive) return;
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
    // Catalog entries are metadata; keep only the finest visible detail plus
    // the broad background resident. Release old textures before adding new ones.
    const visible=entries.slice(1).filter(entry=>{
      const s=entry.state;
      const rectangle=C.Rectangle.fromRadians(s.west_rad,s.south_rad,s.east_rad,s.north_rad);
      return Boolean(view && C.Rectangle.intersection(view,rectangle));
    });
    const wanted=new Set([entries[0],...visible.slice(-(maximumActive-1))]);
    entries.forEach(entry=>{
      entry.wanted=wanted.has(entry);
      if (!entry.wanted && entry.layer) {viewer.imageryLayers.remove(entry.layer,true);entry.layer=null;}
    });
    entries.forEach((entry,index)=>{if(entry.wanted) attach(entry,index);});
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
