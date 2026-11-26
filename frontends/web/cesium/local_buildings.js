/* Presentation of local outlines only. Source height tags are not verified surveys. */
'use strict';
window.ORCLocalBuildings = function (viewer, data, C, heightAt = () => 0) {
  const source = new C.CustomDataSource('buildings');
  viewer.dataSources.add(source);
  const groundUpdates = [];
  const entries = [];
  const counts = {'osm-height':0, 'levels-estimate':0, placeholder:0};
  for (const building of data.buildings) {
    // Flat base sampled at the footprint centroid; coarse terrain is relative relief.
    const ring = building.ring_rad.slice(0,-1);
    const lon = ring.reduce((sum,p) => sum+p[0],0)/ring.length;
    const lat = ring.reduce((sum,p) => sum+p[1],0)/ring.length;
    const base = heightAt(lon,lat);
    const color = building.height_source === 'osm-height' ? '#c7d3d8'
      : building.height_source === 'levels-estimate' ? '#aebcc2' : '#87969c';
    const entity = source.entities.add({polygon:{
      hierarchy:new C.PolygonHierarchy(ring.map(p => C.Cartesian3.fromRadians(p[0],p[1]))),
      height:base, extrudedHeight:base+building.height_m,
      material:C.Color.fromCssColorString(color).withAlpha(.72), outline:false
    }});
    entries.push({entity, source:building.height_source});
    groundUpdates.push(() => {
      const base = heightAt(lon,lat);
      entity.polygon.height = base;
      entity.polygon.extrudedHeight = base+building.height_m;
    });
    counts[building.height_source]++;
  }
  function applyDetail() {
    // Regional views are clearer without a carpet of block geometry. At city
    // scale retain only surveyed/tagged heights; floor estimates join close in.
    // Generic placeholders remain excluded because they convey no real height.
    const cameraHeight = viewer.camera.positionCartographic.height;
    for (const entry of entries) {
      entry.entity.show = cameraHeight <= 15000 && (
        entry.source === 'osm-height'
        || (entry.source === 'levels-estimate' && cameraHeight <= 3000)
      );
    }
    viewer.scene.requestRender();
  }
  const unbindDetail = viewer.camera.changed.addEventListener(applyDetail);
  applyDetail();
  viewer.cesiumWidget.creditDisplay.addStaticCredit(new C.Credit(
    '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · ODbL 1.0',true));
  viewer.scene.requestRender();
  return {
    source,
    refreshGround(){groundUpdates.forEach(update=>update());},
    destroy(){unbindDetail();viewer.dataSources.remove(source,true);},
    label:`Buildings: ${counts['osm-height']} tagged, ${counts['levels-estimate']} floor estimates · placeholders hidden`
  };
};
