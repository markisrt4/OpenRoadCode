/* Local presentation requests orbit the selected place; no location tracking. */
'use strict';
window.ORCCameraControls = function(viewer, target, state, C) {
  function pitch(direction) {
    const camera = viewer.camera;
    const tilt = Math.max(0, Math.min(state.maximum_tilt_rad,
      camera.pitch + Math.PI/2 + direction*state.pitch_step_rad));
    const distance = C.Cartesian3.distance(camera.positionWC, target);
    camera.lookAt(target, new C.HeadingPitchRange(camera.heading, tilt-Math.PI/2, distance));
    camera.lookAtTransform(C.Matrix4.IDENTITY);
    viewer.scene.requestRender();
    return tilt;
  }
  return {pitch};
};
