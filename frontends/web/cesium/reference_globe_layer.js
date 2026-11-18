'use strict';
window.ORCReferenceGlobeLayer = async function(viewer,C) {
  if (viewer.__orcReferenceGlobeLayer) return viewer.__orcReferenceGlobeLayer;
  // Ship one small offline texture: no country polygon rasterization or canvas
  // readback through the Android/Termux graphics stack at viewer startup.
  const pending=(async()=>{
    const provider=await C.SingleTileImageryProvider.fromUrl('/data/world-reference.png',{
      rectangle:C.Rectangle.fromRadians(-Math.PI,-Math.PI/2,Math.PI,Math.PI/2),
      credit:'Natural Earth · public domain · offline world reference'
    });
    provider.orcLayerRole='reference-globe';
    if (viewer.isDestroyed()) return null;
    return viewer.imageryLayers.addImageryProvider(provider,0);
  })();
  viewer.__orcReferenceGlobeLayer=pending;
  return pending;
};
