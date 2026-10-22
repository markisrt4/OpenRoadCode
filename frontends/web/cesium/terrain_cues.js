/* Optional Cesium presentation cues for installed local relief. */
'use strict';
window.ORCTerrainCues = function (viewer, C) {
  const globe = viewer.scene.globe;
  const originalLighting = globe.enableLighting;
  const originalMaterial = globe.material;
  const color=C.Color.fromCssColorString('#e6d59a').withAlpha(.58);
  let scale=1;
  let contours;
  function createContours() {
    return C.Material.fromType('ElevationContour',{color,spacing:10*scale,width:1.25});
  }
  contours=createContours();
  let enabled = false;
  function setEnabled(value) {
    enabled = Boolean(value);
    globe.enableLighting = enabled || originalLighting;
    globe.material = enabled ? contours : originalMaterial;
    viewer.scene.requestRender();
  }
  function setScale(value) {
    if(![1,2,3].includes(value))throw new Error('Terrain cue scale must be 1, 2 or 3');
    if(scale===value)return;
    scale=value;
    contours=createContours();
    if(enabled)globe.material=contours;
    viewer.scene.requestRender();
  }
  return {get enabled(){return enabled;},setEnabled,setScale};
};
