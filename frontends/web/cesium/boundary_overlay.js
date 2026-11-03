'use strict';
window.ORCBoundaryOverlay = function(viewer,state,C) {
  if (!state?.regions?.length) return null;
  const source=new C.CustomDataSource('state-boundaries');
  for (const region of state.regions) for (const ring of region.rings_rad) {
    const color=C.Color.fromCssColorString(region.emphasized?'#59d8ff':'#e7eff6')
      .withAlpha(region.emphasized ? .9 : .45);
    source.entities.add({name:region.name,polyline:{
      positions:C.Cartesian3.fromRadiansArray(ring.flat()),clampToGround:true,
      width:region.emphasized?2.5:1.25,
      material:new C.PolylineDashMaterialProperty({
        color,dashLength:12,dashPattern:0x000f
      })
    }});
  }
  viewer.dataSources.add(source);
  viewer.cesiumWidget.creditDisplay.addStaticCredit(new C.Credit(state.attribution,true));
  viewer.scene.requestRender();
  return {source,destroy(){viewer.dataSources.remove(source,true);}};
};
