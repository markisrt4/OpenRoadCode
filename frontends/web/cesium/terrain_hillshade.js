/* Bounded, offline hillshade imagery derived from installed terrain samples. */
'use strict';
window.ORCTerrainHillshade = function(viewer,data,C,onError=()=>{}) {
  const radius=6371000;
  let enabled=false,disposed=false,lastCheck=0,lastLayerCount=-1;
  const tiles=(data.tiles||[data]).slice();
  const entries=tiles.map(tile=>({tile,layer:null,pending:false,wanted:false,url:null}));
  function imageUrl(entry) {
    if (entry.url) return entry.url;
    const tile=entry.tile;
    const canvas=document.createElement('canvas');
    canvas.width=tile.width;canvas.height=tile.height;
    const context=canvas.getContext('2d');
    const image=context.createImageData(tile.width,tile.height);
    const latitude=(tile.south_rad+tile.north_rad)/2;
    const dx=Math.max(1,radius*Math.cos(latitude)*(tile.east_rad-tile.west_rad)/(tile.width-1));
    const dy=Math.max(1,radius*(tile.north_rad-tile.south_rad)/(tile.height-1));
    const at=(row,col)=>tile.heights_m[row*tile.width+col];
    for(let row=0;row<tile.height;row++) for(let col=0;col<tile.width;col++) {
      const left=Math.max(0,col-1),right=Math.min(tile.width-1,col+1);
      const north=Math.max(0,row-1),south=Math.min(tile.height-1,row+1);
      // Fourfold contrast makes low Michigan slopes legible without changing geometry.
      const gx=4*(at(row,right)-at(row,left))/(Math.max(1,right-left)*dx);
      const gy=4*(at(south,col)-at(north,col))/(Math.max(1,south-north)*dy);
      const length=Math.hypot(gx,gy,1);
      const illumination=(gx*.5+gy*.5+.70710678)/length;
      const delta=illumination-.70710678;
      const offset=(row*tile.width+col)*4;
      const shadow=delta<0;
      image.data[offset]=shadow?12:255;
      image.data[offset+1]=shadow?22:248;
      image.data[offset+2]=shadow?30:220;
      image.data[offset+3]=Math.min(shadow?92:55,Math.round(Math.abs(delta)*(shadow?360:230)));
    }
    context.putImageData(image,0,0);
    entry.url=canvas.toDataURL('image/png');
    return entry.url;
  }
  async function attach(entry) {
    if(entry.layer||entry.pending||disposed||!entry.wanted)return;
    entry.pending=true;
    try {
      const tile=entry.tile;
      const provider=await C.SingleTileImageryProvider.fromUrl(imageUrl(entry),{
        rectangle:C.Rectangle.fromRadians(tile.west_rad,tile.south_rad,tile.east_rad,tile.north_rad),
        credit:data.attribution||tile.attribution});
      if(disposed||viewer.isDestroyed()||!entry.wanted)return;
      entry.layer=viewer.imageryLayers.addImageryProvider(provider);
      viewer.scene.requestRender();
    } catch(error) {if(!disposed)onError(error);} finally {entry.pending=false;}
  }
  function update(force=false) {
    const now=Date.now();
    if(enabled&&viewer.imageryLayers.length!==lastLayerCount) {
      entries.filter(entry=>entry.layer).sort((a,b)=>(a.tile.detail_level||0)-(b.tile.detail_level||0))
        .forEach(entry=>viewer.imageryLayers.raiseToTop(entry.layer));
      lastLayerCount=viewer.imageryLayers.length;
    }
    if(disposed||(!force&&now-lastCheck<500))return;
    lastCheck=now;
    const view=viewer.camera.computeViewRectangle(viewer.scene.globe.ellipsoid);
    const visible=entries.filter(entry=>!view||C.Rectangle.intersection(view,
      C.Rectangle.fromRadians(entry.tile.west_rad,entry.tile.south_rad,entry.tile.east_rad,entry.tile.north_rad)))
      .sort((a,b)=>(b.tile.detail_level||0)-(a.tile.detail_level||0)).slice(0,6);
    const wanted=new Set(enabled?visible:[]);
    entries.forEach(entry=>{
      entry.wanted=wanted.has(entry);
      if(entry.wanted)attach(entry);
      else if(entry.layer){viewer.imageryLayers.remove(entry.layer,true);entry.layer=null;}
    });
    entries.filter(entry=>entry.layer).sort((a,b)=>(a.tile.detail_level||0)-(b.tile.detail_level||0))
      .forEach(entry=>viewer.imageryLayers.raiseToTop(entry.layer));
    lastLayerCount=viewer.imageryLayers.length;
  }
  const remove=viewer.scene.postRender.addEventListener(()=>update());
  return {setEnabled(value){enabled=Boolean(value);update(true);},destroy(){disposed=true;remove();entries.forEach(entry=>{
    if(entry.layer)viewer.imageryLayers.remove(entry.layer,true);
    entry.layer=null;
  });}};
};
