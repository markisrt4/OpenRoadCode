'use strict';
window.ORCReferenceGlobeLayer = async function(viewer,C) {
  if (viewer.__orcReferenceGlobeLayer) return viewer.__orcReferenceGlobeLayer;
  // Reuse the pinned SDK's offline shaded-relief tiles. Keep the small opaque
  // reference image as fallback; neither path rasterizes polygons on the device.
  const pending=(async()=>{
    let provider;
    if(C.TileMapServiceImageryProvider && C.buildModuleUrl) {
      try {
        provider=await C.TileMapServiceImageryProvider.fromUrl(
          C.buildModuleUrl('Assets/Textures/NaturalEarthII'),{
            maximumLevel:2,fileExtension:'jpg',
            credit:'Natural Earth II · public domain · offline shaded-relief overview'
          });
      } catch(error) {
        if(viewer.isDestroyed())return null;
      }
    }
    if(!provider)provider=await C.SingleTileImageryProvider.fromUrl('/data/world-reference.png',{
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
