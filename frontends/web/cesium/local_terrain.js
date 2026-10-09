/* Cesium presentation adapter for coarse local relief, never absolute-height conversion. */
'use strict';
window.ORCLocalTerrain = function (data, C) {
  const scheme = new C.GeographicTilingScheme();
  function heightAt(longitude, latitude) {
    if (longitude<data.west_rad || longitude>data.east_rad || latitude<data.south_rad || latitude>data.north_rad) return 0;
    const x = (longitude-data.west_rad)/(data.east_rad-data.west_rad)*(data.width-1);
    const y = (data.north_rad-latitude)/(data.north_rad-data.south_rad)*(data.height-1);
    const col = Math.min(Math.floor(x),data.width-2), row = Math.min(Math.floor(y),data.height-2);
    const fx=x-col, fy=y-row;
    const at = (r,c) => data.heights_m[r*data.width+c]-data.reference_height_m;
    const value=(at(row,col)*(1-fx)+at(row,col+1)*fx)*(1-fy)+
      (at(row+1,col)*(1-fx)+at(row+1,col+1)*fx)*fy;
    // Fade the boundary to the zero-relief outside region to avoid vertical seams.
    const margin = Math.min(x,y,data.width-1-x,data.height-1-y);
    return value*Math.min(1,Math.max(0,margin));
  }
  const provider = new C.CustomHeightmapTerrainProvider({width:33,height:33,tilingScheme:scheme,
    credit:data.attribution,
    callback:(x,y,level) => {
      const rectangle=scheme.tileXYToRectangle(x,y,level);
      const buffer=new Float32Array(33*33);
      for (let row=0;row<33;row++) for (let col=0;col<33;col++) {
        buffer[row*33+col]=heightAt(rectangle.west+(rectangle.east-rectangle.west)*col/32,
          rectangle.north-(rectangle.north-rectangle.south)*row/32);
      }
      return buffer;
    }
  });
  const geometricError=provider.getLevelMaximumGeometricError.bind(provider);
  // Do not keep subdividing a ~100 m source grid into metre-scale meshes.
  provider.getLevelMaximumGeometricError=level => level>=13 ? 0 : geometricError(level);
  return {provider,heightAt};
};
