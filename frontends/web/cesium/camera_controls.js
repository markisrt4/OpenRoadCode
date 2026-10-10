/* Local presentation requests orbit the ground currently at the view centre. */
'use strict';
window.ORCCameraControls = function(viewer, state, C) {
  function pitch(direction) {
    const camera = viewer.camera;
    const tilt = Math.max(0, Math.min(state.maximum_tilt_rad,
      camera.pitch + Math.PI/2 + direction*state.pitch_step_rad));
    const scene = viewer.scene;
    const centre = new C.Cartesian2(scene.canvas.clientWidth/2, scene.canvas.clientHeight/2);
    const ray = camera.getPickRay(centre);
    const anchor = (ray && scene.globe.pick(ray, scene)) ||
      camera.pickEllipsoid(centre, scene.globe.ellipsoid);
    if (anchor) {
      const distance = C.Cartesian3.distance(camera.positionWC, anchor);
      camera.lookAt(anchor, new C.HeadingPitchRange(camera.heading, tilt-Math.PI/2, distance));
      camera.lookAtTransform(C.Matrix4.IDENTITY);
    } else {
      // Looking at the sky: change orientation in place rather than returning to the POI.
      camera.setView({orientation:{heading:camera.heading,pitch:tilt-Math.PI/2,roll:camera.roll}});
    }
    scene.requestRender();
    return tilt;
  }
  return {pitch};
};
