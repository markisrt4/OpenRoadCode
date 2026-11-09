/* Bounded local building presentation. OSM tags and estimates are not surveys. */
'use strict';
window.ORCLocalBuildings = function (viewer, data, C, heightAt = () => 0) {
  const source = new C.CustomDataSource('buildings');
  viewer.dataSources.add(source);
  const counts = {'osm-height':0, 'levels-estimate':0, placeholder:0};
  const entries = [];
  const active = new Map();
  const budget = 512; // Four streamed tiles => at most 2048 building entities.
  let disposed = false;
  for (const building of data.buildings) {
    counts[building.height_source]++;
    // An outline containing accepted parts is metadata, not a solid roof over
    // the parts. Preserve its source height in the pack for inspection.
    if (building.outline_only) continue;
    const ring = building.ring_rad.slice(0,-1);
    entries.push({building, ring,
      lon:ring.reduce((sum,p) => sum+p[0],0)/ring.length,
      lat:ring.reduce((sum,p) => sum+p[1],0)/ring.length});
  }
  function ground(entry,entity) {
    const base = heightAt(entry.lon,entry.lat);
    entity.polygon.height = base+(entry.building.min_height_m || 0);
    entity.polygon.extrudedHeight = base+entry.building.height_m;
  }
  function create(entry) {
    const building=entry.building;
    const color = building.height_source === 'osm-height' ? '#c7d3d8'
      : building.height_source === 'levels-estimate' ? '#aebcc2' : '#87969c';
    const entity = source.entities.add({polygon:{
      hierarchy:new C.PolygonHierarchy(entry.ring.map(p => C.Cartesian3.fromRadians(p[0],p[1])),
        (building.holes_rad || []).map(hole => new C.PolygonHierarchy(
          hole.slice(0,-1).map(p => C.Cartesian3.fromRadians(p[0],p[1]))))),
      material:C.Color.fromCssColorString(color).withAlpha(.72), outline:false
    }});
    ground(entry,entity);
    return entity;
  }
  function applyDetail() {
    if (disposed) return;
    const camera = viewer.camera.positionCartographic;
    const anchor = window.ORCCameraGroundAnchor?.(viewer,C)
      || window.ORCCameraGroundAnchor?.(viewer,C,.75)
      || window.ORCCameraGroundAnchor?.(viewer,C,.9);
    const center = anchor ? C.Cartographic.fromCartesian(anchor) : camera;
    const ranked=[];
    for (const entry of entries) {
      const kind=entry.building.height_source;
      const limit=kind==='osm-height' ? 15000 : kind==='levels-estimate' ? 3000 : 1500;
      if (camera.height>limit) continue;
      const distance=Math.hypot((entry.lon-center.longitude)*Math.cos(center.latitude),
        entry.lat-center.latitude)*6371000;
      if(kind==='placeholder' && distance>2000)continue;
      ranked.push({entry,distance,priority:kind==='osm-height'?0:kind==='levels-estimate'?1:2});
    }
    ranked.sort((a,b)=>a.priority-b.priority || a.distance-b.distance);
    const wanted=new Set(ranked.slice(0,budget).map(item=>item.entry));
    for (const [entry,entity] of active) if(!wanted.has(entry)) {
      source.entities.remove(entity);active.delete(entry);
    }
    for (const entry of wanted) if(!active.has(entry)) active.set(entry,create(entry));
    viewer.scene.requestRender();
  }
  // Reconcile at the end of a camera gesture, avoiding repeated geometry
  // allocation while panning/tilting. Reuse the existing camera event lifecycle.
  const unbindDetail = (viewer.camera.moveEnd || viewer.camera.changed).addEventListener(applyDetail);
  applyDetail();
  viewer.cesiumWidget.creditDisplay.addStaticCredit(new C.Credit(
    '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · ODbL 1.0',true));
  return {
    source,
    refreshGround(){for(const [entry,entity] of active)ground(entry,entity);},
    destroy(){disposed=true;unbindDetail();active.clear();viewer.dataSources.remove(source,true);},
    label:`Buildings: ${counts['osm-height']} tagged, ${counts['levels-estimate']} floor estimates, ${counts.placeholder} approximate · detail limited to ${budget} per tile`
  };
};
