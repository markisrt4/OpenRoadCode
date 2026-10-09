/* Presentation of local outlines only. Source height tags are not verified surveys. */
'use strict';
window.ORCLocalBuildings = function (viewer, data, C, heightAt = () => 0) {
  const counts = {'osm-height':0, 'levels-estimate':0, placeholder:0};
  for (const building of data.buildings) {
    // Flat base sampled at the footprint centroid; coarse terrain is relative relief.
    const ring = building.ring_rad.slice(0,-1);
    const lon = ring.reduce((sum,p) => sum+p[0],0)/ring.length;
    const lat = ring.reduce((sum,p) => sum+p[1],0)/ring.length;
    const base = heightAt(lon,lat);
    const color = building.height_source === 'osm-height' ? '#c4dce8'
      : building.height_source === 'levels-estimate' ? '#d7bb79' : '#bd8b66';
    viewer.entities.add({polygon:{
      hierarchy:new C.PolygonHierarchy(ring.map(p => C.Cartesian3.fromRadians(p[0],p[1]))),
      height:base, extrudedHeight:base+building.height_m,
      material:C.Color.fromCssColorString(color), outline:false
    }});
    counts[building.height_source]++;
  }
  viewer.cesiumWidget.creditDisplay.addStaticCredit(new C.Credit(
    '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · ODbL 1.0',true));
  viewer.scene.requestRender();
  return `Buildings: ${counts['osm-height']} tagged (blue), ${counts['levels-estimate']} floor estimates (gold), ${counts.placeholder} 9 m placeholders (brown)`;
};
