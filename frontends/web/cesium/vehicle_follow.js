'use strict';
window.ORCVehicleFollow = function(viewer, state, C, heightAt=()=>0) {
    const vehicle = viewer.entities.add({show:false,
      point:{pixelSize:12,color:C.Color.YELLOW,outlineColor:C.Color.BLACK,outlineWidth:2,
             disableDepthTestDistance:Infinity},
      label:{text:'Vehicle',font:'13px sans-serif',pixelOffset:new C.Cartesian2(0,-22),
             disableDepthTestDistance:Infinity}});
    return (position, follow) => {
      if (!position) { vehicle.show=false; viewer.scene.requestRender(); return true; }
      const ground = heightAt(position.longitude_rad,position.latitude_rad) || 0;
      const next = C.Cartesian3.fromRadians(position.longitude_rad,position.latitude_rad,ground+2);
      vehicle.position = next;
      vehicle.show = true;
      if (follow) {
        const camera = viewer.camera;
        const centre = new C.Cartesian2(viewer.scene.canvas.clientWidth/2,viewer.scene.canvas.clientHeight/2);
        const ray = camera.getPickRay(centre);
        const anchor = (ray && viewer.scene.globe.pick(ray,viewer.scene)) || camera.pickEllipsoid(centre);
        const distance = anchor ? C.Cartesian3.distance(camera.positionWC,anchor) : state.distance_m;
        const followTarget = C.Cartesian3.fromRadians(position.longitude_rad,position.latitude_rad,ground);
        camera.lookAt(followTarget,new C.HeadingPitchRange(camera.heading,camera.pitch,Math.max(50,distance)));
        camera.lookAtTransform(C.Matrix4.IDENTITY);
      }
      viewer.scene.requestRender();
      return true;
    };
};
