/* Cesium presentation adapter for coarse local relief, never absolute-height conversion. */
'use strict';
window.ORCLocalTerrain = function (data, C) {
  let scale = 1;
  let visible = true;
  const scheme = new C.GeographicTilingScheme();
  const tiles = (data.tiles || [data]).slice().sort((a,b)=>(b.detail_level||0)-(a.detail_level||0));
  function sample(tile,longitude,latitude) {
    const x = (longitude-tile.west_rad)/(tile.east_rad-tile.west_rad)*(tile.width-1);
    const y = (tile.north_rad-latitude)/(tile.north_rad-tile.south_rad)*(tile.height-1);
    const col = Math.min(Math.floor(x),tile.width-2), row = Math.min(Math.floor(y),tile.height-2);
    const fx=x-col, fy=y-row;
    const at = (r,c) => tile.heights_m[r*tile.width+c]-tile.reference_height_m;
    const value=(at(row,col)*(1-fx)+at(row,col+1)*fx)*(1-fy)+
      (at(row+1,col)*(1-fx)+at(row+1,col+1)*fx)*fy;
    // Fade the boundary to the zero-relief outside region to avoid vertical seams.
    // A single pack fades at its outer boundary. Mosaic tile edges stay continuous.
    const margin = tiles.length === 1 ? Math.min(x,y,tile.width-1-x,tile.height-1-y) : 1;
    return scale*value*Math.min(1,Math.max(0,margin));
  }
  function sampledHeightAt(longitude, latitude, zoom=Infinity) {
    const tile = tiles.find(item => (item.minimum_zoom||0)<=zoom
      && longitude>=item.west_rad && longitude<=item.east_rad
      && latitude>=item.south_rad && latitude<=item.north_rad);
    return tile ? sample(tile,longitude,latitude) : 0;
  }
  function heightAt(longitude, latitude) {
    return visible ? sampledHeightAt(longitude, latitude) : 0;
  }
  function createProvider() {
    const provider = new C.CustomHeightmapTerrainProvider({width:33,height:33,tilingScheme:scheme,
      credit:data.attribution,
      callback:(x,y,level) => {
        const rectangle=scheme.tileXYToRectangle(x,y,level);
        const buffer=new Float32Array(33*33);
        for (let row=0;row<33;row++) for (let col=0;col<33;col++) {
          buffer[row*33+col]=sampledHeightAt(rectangle.west+(rectangle.east-rectangle.west)*col/32,
            rectangle.north-(rectangle.north-rectangle.south)*row/32,level);
        }
        return buffer;
      }
    });
    const geometricError=provider.getLevelMaximumGeometricError.bind(provider);
    // Do not keep subdividing a ~100 m source grid into metre-scale meshes.
    const maximumZoom=data.maximum_zoom||13;
    provider.getLevelMaximumGeometricError=level => level>=maximumZoom ? 0 : geometricError(level);
    return provider;
  }
  let provider = createProvider();
  const flat = new C.EllipsoidTerrainProvider();
  function setVisible(viewer, value) {
    visible = value;
    viewer.terrainProvider = visible ? provider : flat;
    viewer.scene.requestRender();
  }
  function setScale(viewer, value) {
    if (![1,2,3].includes(value)) throw new Error('Terrain scale must be 1, 2 or 3');
    if (scale === value) return;
    scale = value;
    // Replacing the provider invalidates already generated terrain meshes.
    provider = createProvider();
    viewer.terrainProvider = visible ? provider : flat;
    viewer.scene.requestRender();
  }
  return {get provider(){return provider;},heightAt,setVisible,setScale};
};
