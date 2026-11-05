'use strict';
window.ORCReferenceGlobeLayer = async function(viewer,C) {
  if (viewer.__orcReferenceGlobeLayer) return viewer.__orcReferenceGlobeLayer;
  const pending=(async()=>{
    const [landResponse,lakeResponse]=await Promise.all([
      fetch('/data/world-land.geojson'),fetch('/data/world-lakes.geojson')]);
    if (!landResponse.ok || !lakeResponse.ok) throw new Error('Offline globe reference unavailable');
    const [collection,lakes]=await Promise.all([landResponse.json(),lakeResponse.json()]);
    const canvas=document.createElement('canvas');
    canvas.width=2048;canvas.height=1024;
    const context=canvas.getContext('2d');
    context.fillStyle='#174963';context.fillRect(0,0,canvas.width,canvas.height);
    context.fillStyle='#456f4e';
    const point=([longitude,latitude])=>[
      (longitude+180)*canvas.width/360,(90-latitude)*canvas.height/180];
    function fill(collection,color) {
      context.fillStyle=color;
      for (const feature of collection.features||[]) {
      const geometry=feature.geometry||{};
      const polygons=geometry.type==='Polygon'?[geometry.coordinates]:
        geometry.type==='MultiPolygon'?geometry.coordinates:[];
      context.beginPath();
      for (const polygon of polygons) for (const ring of polygon) {
        ring.forEach((coordinate,index)=>{
          const [x,y]=point(coordinate);if(index)context.lineTo(x,y);else context.moveTo(x,y);
        });
        context.closePath();
      }
      context.fill('evenodd');
      }
    }
    fill(collection,'#456f4e');
    fill(lakes,'#174963');
    const provider=await C.SingleTileImageryProvider.fromUrl(canvas.toDataURL('image/png'),{
    rectangle:C.Rectangle.fromRadians(-Math.PI,-Math.PI/2,Math.PI,Math.PI/2)
    });
    if (viewer.isDestroyed()) return null;
    return viewer.imageryLayers.addImageryProvider(provider,0);
  })();
  viewer.__orcReferenceGlobeLayer=pending;
  return pending;
};
