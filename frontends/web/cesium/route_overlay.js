'use strict';
window.ORCRouteOverlay = function(viewer,C,heightAt=()=>0) {
  const source=new C.CustomDataSource('active-route');
  viewer.dataSources.add(source);
  const position=point=>C.Cartesian3.fromRadians(point.longitude_rad,point.latitude_rad,
    heightAt(point.longitude_rad,point.latitude_rad)+3);
  function update(state) {
    if(!state || !Array.isArray(state.points))return false;
    source.entities.removeAll();
    if(state.points.length>1) {
      const positions=state.points.map(position);
      const routeColor=C.Color.fromCssColorString(state.off_route?'#ff633f':'#35bfff');
      source.entities.add({id:'route-casing',polyline:{positions,width:9,
        material:C.Color.BLACK.withAlpha(.72),clampToGround:true}});
      source.entities.add({id:'route-line',polyline:{positions,width:5,
        material:routeColor,clampToGround:true}});
    }
    if(state.destination) source.entities.add({id:'route-destination',position:position(state.destination),
      point:{pixelSize:13,color:C.Color.fromCssColorString('#bfff55'),outlineColor:C.Color.BLACK,
        outlineWidth:3,disableDepthTestDistance:Number.POSITIVE_INFINITY}});
    if(state.maneuver && !state.route_complete) source.entities.add({id:'route-maneuver',position:position(state.maneuver),
      point:{pixelSize:12,color:C.Color.fromCssColorString('#ffd24a'),outlineColor:C.Color.BLACK,
        outlineWidth:3,disableDepthTestDistance:Number.POSITIVE_INFINITY},
      label:{text:String(state.instruction||'Next maneuver').slice(0,240),font:'bold 12px sans-serif',
        pixelOffset:new C.Cartesian2(0,-20),fillColor:C.Color.WHITE,outlineColor:C.Color.BLACK,
        outlineWidth:3,style:C.LabelStyle.FILL_AND_OUTLINE,showBackground:true,
        backgroundColor:C.Color.BLACK.withAlpha(.72),distanceDisplayCondition:new C.DistanceDisplayCondition(0,10000),
        disableDepthTestDistance:Number.POSITIVE_INFINITY}});
    viewer.scene.requestRender();
    return true;
  }
  return {source,update,destroy(){viewer.dataSources.remove(source,true);}};
};
