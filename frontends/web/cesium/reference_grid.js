/* Synthetic local reference geometry, expressed in metres in the destination's ENU frame. */
'use strict';
window.ORCCesiumReferences = function (viewer, snapshot, C) {
  const origin = C.Cartesian3.fromRadians(snapshot.longitude_rad, snapshot.latitude_rad);
  const frame = C.Transforms.eastNorthUpToFixedFrame(origin);
  function position(east, north) {
    const point = C.Matrix4.multiplyByPoint(frame, new C.Cartesian3(east, north, 0), new C.Cartesian3());
    const ground = C.Ellipsoid.WGS84.cartesianToCartographic(point);
    // Lift reference graphics slightly above the ellipsoid to prevent depth flicker.
    return C.Cartesian3.fromRadians(ground.longitude, ground.latitude, 3);
  }
  function line(points, material, width=1) {
    viewer.entities.add({polyline:{positions:points.map(([east,north]) => position(east,north)),
      width, material}});
  }
  function label(east, north, text, color=C.Color.WHITE) {
    viewer.entities.add({position:position(east,north),label:{text,font:'bold 15px sans-serif',
      fillColor:color,showBackground:true,backgroundColor:C.Color.BLACK.withAlpha(.65),
      pixelOffset:new C.Cartesian2(0,-12),disableDepthTestDistance:Number.POSITIVE_INFINITY}});
  }
  const extent = 1000;
  const spacing = 250;
  for (let east=-extent; east<extent; east+=spacing) {
    for (let north=-extent; north<extent; north+=spacing) {
      if ((east/spacing+north/spacing)%2 === 0) {
        const corners = [[east,north],[east+spacing,north],
          [east+spacing,north+spacing],[east,north+spacing]];
        viewer.entities.add({polygon:{hierarchy:new C.PolygonHierarchy(corners.map(([x,y]) => position(x,y))),
          perPositionHeight:true,material:C.Color.WHITE.withAlpha(.08)}});
      }
    }
  }
  for (let offset=-extent; offset<=extent; offset+=spacing) {
    line([[offset,-extent],[offset,extent]], C.Color.WHITE.withAlpha(.45));
    line([[-extent,offset],[extent,offset]], C.Color.WHITE.withAlpha(.45));
  }
  for (const radius of [250,500,1000]) {
    const points = [];
    for (let step=0; step<=96; step++) {
      const angle = step/96*Math.PI*2;
      points.push([Math.cos(angle)*radius, Math.sin(angle)*radius]);
    }
    line(points, C.Color.fromCssColorString('#78e0ff'), 2);
    label(radius/Math.sqrt(2), -radius/Math.sqrt(2), `${radius} m`);
  }
  line([[0,0],[0,1150]], new C.PolylineArrowMaterialProperty(C.Color.YELLOW), 8);
  line([[0,0],[1150,0]], C.Color.CYAN, 3);
  label(0,1200,'N · North',C.Color.YELLOW);
  label(1200,0,'E · East',C.Color.CYAN);
  label(-1100,0,'W');
  label(0,-1100,'S');
  label(-750,750,'NW');
  label(750,750,'NE');
  label(-750,-750,'SW');
  label(750,-750,'SE');
  label(0,-1400,'Reference grid · 250 m squares');
};
