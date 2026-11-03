'use strict';
window.ORCReferenceGlobeLayer = async function(viewer,C) {
  const bluePng='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGMU90xmYGBgYmBgYGBgAAAJAgDHgWq2kAAAAABJRU5ErkJggg==';
  const provider=await C.SingleTileImageryProvider.fromUrl(bluePng,{
    rectangle:C.Rectangle.fromRadians(-Math.PI,-Math.PI/2,Math.PI,Math.PI/2)
  });
  if (viewer.isDestroyed()) return null;
  return viewer.imageryLayers.addImageryProvider(provider,0);
};
