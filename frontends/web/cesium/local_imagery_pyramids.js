/* Zoom-dependent imagery tiles; Cesium owns requests and the bounded globe cache. */
'use strict';
window.ORCImageryPyramids = function(viewer, states, C) {
  const layers=[];
  let disposed=false;
  if (!states.length) return {destroy(){}};
  viewer.scene.globe.tileCacheSize=64;
  C.RequestScheduler.maximumRequestsPerServer=6;
  const raise=()=>{
    if(disposed || viewer.isDestroyed())return;
    for(const layer of layers)if(viewer.imageryLayers.contains(layer))viewer.imageryLayers.raiseToTop(layer);
  };
  // Coarse layers may complete after this controller; keep detail above them.
  const unbind=viewer.imageryLayers.layerAdded.addEventListener(raise);
  for(const state of states) {
    const provider=new C.UrlTemplateImageryProvider({url:state.url,
      rectangle:C.Rectangle.fromRadians(state.west_rad,state.south_rad,state.east_rad,state.north_rad),
      tilingScheme:new C.WebMercatorTilingScheme(),minimumLevel:state.minimum_zoom,
      maximumLevel:state.maximum_zoom,tileWidth:state.tile_size,tileHeight:state.tile_size,
      credit:state.attribution});
    provider.orcLayerRole='imagery-detail';
    layers.push(viewer.imageryLayers.addImageryProvider(provider));
  }
  raise();
  return {destroy(){
    if(disposed)return;
    disposed=true;unbind();
    for(const layer of layers)viewer.imageryLayers.remove(layer,true);
    layers.length=0;
  }};
};
