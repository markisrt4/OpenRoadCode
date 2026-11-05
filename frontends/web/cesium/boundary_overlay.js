'use strict';
window.ORCBoundaryOverlay = function(viewer,state,C) {
  if (!state?.regions?.length) return null;
  const source=new C.CustomDataSource('state-boundaries');
  for (const region of state.regions) for (const path of region.paths_rad) {
    const country=region.kind==='country',disputed=region.kind==='disputed';
    const color=C.Color.fromCssColorString(region.emphasized?'#59d8ff':country?'#f1f5f8':disputed?'#ffca72':'#e7eff6')
      .withAlpha(region.emphasized ? .9 : country ? .62 : disputed ? .7 : .45);
    source.entities.add({name:region.name,polyline:{
      positions:C.Cartesian3.fromRadiansArray(path.flat()),clampToGround:true,
      width:region.emphasized?2.5:country?1.8:disputed?1.6:1.25,
      material:new C.PolylineDashMaterialProperty({
        color,dashLength:country?18:12,dashPattern:disputed?0x00ff:country?0x0fff:0x000f
      })
    }});
  }
  viewer.dataSources.add(source);
  viewer.cesiumWidget.creditDisplay.addStaticCredit(new C.Credit(state.attribution,true));
  viewer.scene.requestRender();
  return {source,destroy(){viewer.dataSources.remove(source,true);}};
};
