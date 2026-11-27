'use strict';
window.ORCPoiOverlay = function(viewer,C,heightAt=()=>0) {
  const source=new C.CustomDataSource('dynamic-pois');
  const markerIds=new Map();
  const nameLabels=new Map();
  const styles={fuel:['#f15a16','⛽'],grocery:['#84ce1f','▣'],food:['#d49a38','☕'],
    bus:['#376fd8','▴'],rail:['#7a5bd8','◆'],'tram-subway':['#d84fa3','◆'],
    transit:['#376fd8','◆']};
  let selected=null;
  let focused=null;
  viewer.dataSources.add(source);
  function update(state) {
    if(!state || !Array.isArray(state.markers))return false;
    source.entities.removeAll();
    markerIds.clear();nameLabels.clear();focused=null;
    const style=styles[String(state.category||'').toLowerCase()]||['#777777','◆'];
    for(const marker of state.markers) {
      const markerId=String(marker.id);
      const suffix=markerId.slice(0,160);
      const entityId='poi-'+suffix;
      const position=C.Cartesian3.fromRadians(marker.longitude_rad,marker.latitude_rad,
        heightAt(marker.longitude_rad,marker.latitude_rad)+12);
      markerIds.set(entityId,markerId);
      source.entities.add({id:entityId,position,
        point:{pixelSize:19,color:C.Color.fromCssColorString(style[0]),
          outlineColor:C.Color.WHITE,outlineWidth:1.5,
          disableDepthTestDistance:Number.POSITIVE_INFINITY},
        label:{text:style[1],font:'bold 14px sans-serif',pixelOffset:new C.Cartesian2(0,1),
          fillColor:C.Color.WHITE,outlineColor:C.Color.BLACK,outlineWidth:1,
          style:C.LabelStyle.FILL_AND_OUTLINE,
          disableDepthTestDistance:Number.POSITIVE_INFINITY}});
      const label=source.entities.add({id:'poi-label-'+suffix,show:false,position,
        label:{text:String(marker.label||'Place').slice(0,120),font:'bold 12px sans-serif',
          pixelOffset:new C.Cartesian2(0,-24),fillColor:C.Color.fromCssColorString('#202020'),
          outlineColor:C.Color.WHITE,outlineWidth:3,style:C.LabelStyle.FILL_AND_OUTLINE,
          showBackground:true,backgroundColor:C.Color.WHITE.withAlpha(.86),
          distanceDisplayCondition:new C.DistanceDisplayCondition(0,10000),
          disableDepthTestDistance:Number.POSITIVE_INFINITY}});
      markerIds.set(label.id,markerId);
      nameLabels.set(markerId,label);
    }
    viewer.scene.requestRender();
    return true;
  }
  function focus(entityId) {
    const markerId=markerIds.get(String(entityId||''))||null;
    if(focused!==markerId) {
      if(focused && nameLabels.has(focused))nameLabels.get(focused).show=false;
      focused=markerId;
      if(focused && nameLabels.has(focused))nameLabels.get(focused).show=true;
      viewer.scene.requestRender();
    }
    return markerId!==null;
  }
  function select(entityId) {
    const markerId=markerIds.get(String(entityId||''));
    if(!markerId)return false;
    focus(entityId);selected=markerId;return true;
  }
  function consumeSelection() {const value=selected;selected=null;return value;}
  return {source,update,select,focus,consumeSelection,
    destroy(){viewer.dataSources.remove(source,true);}};
};
