'use strict';
window.ORCPoiOverlay = function(viewer,C,heightAt=()=>0) {
  const source=new C.CustomDataSource('dynamic-pois');
  viewer.dataSources.add(source);
  function update(state) {
    if(!state || !Array.isArray(state.markers))return false;
    source.entities.removeAll();
    for(const marker of state.markers) {
      const label=String(marker.label||'Place').slice(0,120);
      source.entities.add({id:'poi-'+String(marker.id).slice(0,160),
        position:C.Cartesian3.fromRadians(marker.longitude_rad,marker.latitude_rad,
          heightAt(marker.longitude_rad,marker.latitude_rad)+18),
        point:{pixelSize:11,color:C.Color.fromCssColorString('#bfff55'),
          outlineColor:C.Color.BLACK,outlineWidth:2,
          disableDepthTestDistance:Number.POSITIVE_INFINITY},
        label:{text:label,font:'bold 12px sans-serif',pixelOffset:new C.Cartesian2(0,-20),
          fillColor:C.Color.WHITE,outlineColor:C.Color.BLACK,outlineWidth:3,
          style:C.LabelStyle.FILL_AND_OUTLINE,showBackground:true,
          backgroundColor:C.Color.BLACK.withAlpha(.72),
          distanceDisplayCondition:new C.DistanceDisplayCondition(0,12000),
          disableDepthTestDistance:Number.POSITIVE_INFINITY}});
    }
    viewer.scene.requestRender();
    return true;
  }
  return {source,update,destroy(){viewer.dataSources.remove(source,true);}};
};
