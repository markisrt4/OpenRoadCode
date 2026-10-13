/* Local presentation requests orbit the ground currently at the view centre. */
'use strict';
window.ORCCameraControls = function(viewer, state, C, heightAt=()=>0) {
  function pitch(direction, absoluteTilt=undefined) {
    const camera = viewer.camera;
    const tilt = Math.max(0, Math.min(state.maximum_tilt_rad,
      absoluteTilt ?? (camera.pitch + Math.PI/2 + direction*state.pitch_step_rad)));
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
  function pan(right, up) {
    const camera = viewer.camera;
    const scene = viewer.scene;
    const centre = new C.Cartesian2(scene.canvas.clientWidth/2, scene.canvas.clientHeight/2);
    const ray = camera.getPickRay(centre);
    const anchor = (ray && scene.globe.pick(ray, scene)) || camera.pickEllipsoid(centre, scene.globe.ellipsoid);
    if (!anchor) return false;
    const distance = C.Cartesian3.distance(camera.positionWC, anchor);
    const step = Math.max(25, Math.min(100000, distance*state.pan_step_fraction));
    const ground = C.Cartographic.fromCartesian(anchor);
    const east = (right*Math.cos(camera.heading)+up*Math.sin(camera.heading))*step;
    const north = (-right*Math.sin(camera.heading)+up*Math.cos(camera.heading))*step;
    const radius = scene.globe.ellipsoid.maximumRadius;
    const latitude = Math.max(-Math.PI/2+1e-6, Math.min(Math.PI/2-1e-6, ground.latitude+north/radius));
    const rawLongitude = ground.longitude+east/(radius*Math.max(.01,Math.cos(ground.latitude)));
    const longitude = ((rawLongitude+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI;
    const next = C.Cartesian3.fromRadians(longitude,latitude,heightAt(longitude,latitude));
    camera.lookAt(next, new C.HeadingPitchRange(camera.heading,camera.pitch,distance));
    camera.lookAtTransform(C.Matrix4.IDENTITY);
    scene.requestRender();
    return true;
  }
  return {pitch,pan};
};
