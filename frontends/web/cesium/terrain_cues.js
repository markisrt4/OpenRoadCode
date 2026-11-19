/* Optional Cesium presentation cues for installed local relief. */
'use strict';
window.ORCTerrainCues = function (viewer, C) {
  const globe = viewer.scene.globe;
  const originalLighting = globe.enableLighting;
  const originalMaterial = globe.material;
  // Keep contours cool and subdued so they cannot be mistaken for the
  // yellow/white navigation road hierarchy.
  const color=C.Color.fromCssColorString('#69a7bd').withAlpha(.46);
  let scale=1;
  let contours;
  function createContours() {
    // Globe materials also run over lakes and oceans. Locate this fragment in
    // the bundled opaque land/lake reference rather than treating all relief
    // as land. The source is an overview mask, not a shoreline survey.
    // WGS84 inverse-radii-squared ratio, rescaled to avoid tiny constants.
    // The globe-only uniform is not exposed inside composed fabric materials.
    const normal='czm_geodeticSurfaceNormal((czm_inverseView*vec4(-materialInput.positionToEyeEC,1.0)).xyz,vec3(0.0),vec3(1.0,1.0,1.0067394967422765))';
    const uv=`czm_ellipsoidTextureCoordinates(${normal})`;
    const water=`texture(waterReference,${uv})`;
    return new C.Material({fabric:{
      type:'ORCLandContours',
      uniforms:{waterReference:'/data/world-reference.png'},
      materials:{contours:{type:'ElevationContour',uniforms:{color,spacing:10*scale,width:1.0}}},
      components:{diffuse:'contours.diffuse',emission:'contours.emission',
        alpha:`contours.alpha*(1.0-max(materialInput.waterMask,step(${water}.g,${water}.b)))`}
    }});

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
    if(![1,2,3,4].includes(value))throw new Error('Terrain cue scale must be 1, 2, 3 or 4');
    if(scale===value)return;
    scale=value;
    contours.materials.contours.uniforms.spacing=10*scale;
    viewer.scene.requestRender();
  }
  return {get enabled(){return enabled;},setEnabled,setScale};
};
