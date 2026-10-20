/* Optional Cesium presentation cues for installed local relief. */
'use strict';
window.ORCTerrainCues = function (viewer, C) {
  const globe = viewer.scene.globe;
  const originalLighting = globe.enableLighting;
  const originalMaterial = globe.material;
  const contours = C.Material.fromType('ElevationContour', {
    color:C.Color.fromCssColorString('#e6d59a').withAlpha(.58),
    spacing:10,
    width:1.25
  });
  let enabled = false;
  function setEnabled(value) {
    enabled = Boolean(value);
    globe.enableLighting = enabled || originalLighting;
    globe.material = enabled ? contours : originalMaterial;
    viewer.scene.requestRender();
  }
  return {get enabled(){return enabled;},setEnabled};
};
