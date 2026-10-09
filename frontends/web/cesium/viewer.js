/* Presentation only: immutable destination snapshot, local SDK, no hosted layers. */
'use strict';
(async function () {
  const status = document.getElementById('status');
  let viewer;
  let snapshot;
  let closing = false;
  const close = document.getElementById('close');
  document.querySelectorAll('nav button').forEach(button => { button.disabled = true; });
  close.disabled = true;
  try {
    const response = await fetch('/config.json');
    if (!response.ok) throw new Error('Unable to load the destination');
    snapshot = await response.json();
    close.disabled = false;
    close.onclick = async () => {
      if (closing) return;
      closing = true;
      close.disabled = true;
      try {
        const result = await fetch('/close', {method:'POST', headers:{'X-ORC-Token':snapshot.close_token}});
        if (!result.ok) throw new Error('Close request failed');
        status.textContent = 'Returning to ORC…';
      } catch (error) {
        status.textContent = error.message + '; use the window close button';
        closing = false;
        close.disabled = false;
      }
    };
    const C = window.Cesium;
    if (!C) throw new Error('Local Cesium SDK did not load');
    C.Ion.defaultAccessToken = '';
    viewer = new C.Viewer('map', {
      baseLayer:false, terrainProvider:new C.EllipsoidTerrainProvider(),
      geocoder:false, baseLayerPicker:false, animation:false, timeline:false,
      homeButton:false, navigationHelpButton:false, fullscreenButton:false,
      sceneModePicker:false, infoBox:false, selectionIndicator:false,
      requestRenderMode:true, maximumRenderTimeChange:Infinity,
      contextOptions:{webgl:{powerPreference:'high-performance'}}
    });
    const terrain = snapshot.terrain ? window.ORCLocalTerrain(snapshot.terrain,C) : null;
    if (terrain) viewer.terrainProvider = terrain.provider;
    viewer.scene.globe.baseColor = C.Color.fromCssColorString('#174963');
    const groundHeight = terrain ? terrain.heightAt(snapshot.longitude_rad,snapshot.latitude_rad) : 0;
    const target = C.Cartesian3.fromRadians(snapshot.longitude_rad, snapshot.latitude_rad,groundHeight+3);
    document.getElementById('destination').textContent = snapshot.label;
    viewer.entities.add({position:target,
      point:{pixelSize:10,color:C.Color.CYAN,outlineColor:C.Color.WHITE,outlineWidth:2},
      label:{text:snapshot.label,font:'16px sans-serif',pixelOffset:new C.Cartesian2(0,-24)}});
    // Procedural geographic grid: no imagery, terrain service, or building data.
    for (let lat = -60; lat <= 60; lat += 30) {
      const points = [];
      for (let lon = -180; lon <= 180; lon += 3) points.push(C.Cartesian3.fromDegrees(lon,lat));
      viewer.entities.add({polyline:{positions:points,width:1,material:C.Color.WHITE.withAlpha(.18)}});
    }
    for (let lon = -180; lon < 180; lon += 30) {
      const points = [];
      for (let lat = -90; lat <= 90; lat += 3) points.push(C.Cartesian3.fromDegrees(lon,lat));
      viewer.entities.add({polyline:{positions:points,width:1,material:C.Color.WHITE.withAlpha(.18)}});
    }
    window.ORCCesiumReferences(viewer, snapshot, C, terrain?.heightAt);
    const buildingLabel = snapshot.buildings
      ? window.ORCLocalBuildings(viewer, snapshot.buildings, C, terrain?.heightAt)
      : "buildings not installed";
    viewer.scene.postRender.addEventListener(() => {
      const height = Math.round(viewer.camera.positionCartographic.height);
      const tilt = Math.round(C.Math.toDegrees(viewer.camera.pitch)+90);
      const heading = Math.round(C.Math.toDegrees(viewer.camera.heading))%360;
      const text = `Scene height ${height.toLocaleString()} m · tilt ${tilt}° · heading ${heading}°`;
      const readout = document.getElementById('camera');
      if (readout.textContent !== text) readout.textContent = text;
    });
    let tilted = true;
    function reset() {
      viewer.camera.lookAt(target, new C.HeadingPitchRange(0,
        tilted ? snapshot.tilt_rad-Math.PI/2 : -Math.PI/2, snapshot.distance_m));
      viewer.camera.lookAtTransform(C.Matrix4.IDENTITY);
      viewer.scene.requestRender();
    }
    document.getElementById('reset').onclick = () => { tilted=true; reset(); };
    document.getElementById('tilt').onclick = () => { tilted=!tilted; reset(); };
    document.getElementById('north').onclick = () => {
      viewer.camera.setView({orientation:{heading:0,pitch:viewer.camera.pitch,roll:0}});
      viewer.scene.requestRender();
    };
    document.getElementById('zoom-in').onclick = () => {
      viewer.camera.zoomIn(Math.max(50,viewer.camera.positionCartographic.height*.25));
      viewer.scene.requestRender();
    };
    document.getElementById('zoom-out').onclick = () => {
      viewer.camera.zoomOut(Math.max(50,viewer.camera.positionCartographic.height*.25));
      viewer.scene.requestRender();
    };
    viewer.scene.renderError.addEventListener((_scene,error) => {
      status.textContent = 'Rendering stopped: '+error.message+' — return and retry';
    });
    document.querySelectorAll('nav button').forEach(button => { button.disabled = false; });
    reset();
    const terrainLabel = terrain ? 'relative relief (~100 m samples)' : 'terrain not installed';
    status.textContent = `Offline reference globe · imagery not installed · ${terrainLabel} · ${buildingLabel}`;
    if (snapshot.imagery) {
      const layer = snapshot.imagery;
      try {
        const provider = await C.SingleTileImageryProvider.fromUrl(layer.url, {
          rectangle:C.Rectangle.fromRadians(layer.west_rad,layer.south_rad,layer.east_rad,layer.north_rad),
          credit:layer.attribution
        });
        if (closing || viewer.isDestroyed()) return;
        // A transparent global base prevents Cesium stretching the first
        // bounded image layer across uncovered parts of the globe.
        viewer.imageryLayers.addImageryProvider(new C.GridImageryProvider({
          color:C.Color.TRANSPARENT, glowColor:C.Color.TRANSPARENT,
          backgroundColor:C.Color.TRANSPARENT, cells:1
        }));
        viewer.imageryLayers.addImageryProvider(provider);
        viewer.scene.requestRender();
        status.textContent = `Offline · ${layer.title} · ${terrainLabel} · ${buildingLabel}`;
      } catch (error) {
        if (!closing) status.textContent = 'Imagery unavailable: '+error.message+' · reference globe remains usable';
      }
    }
  } catch (error) {
    status.textContent = 'Unable to render: '+error.message+' — use Return to ORC or the window close button';
  }
  window.addEventListener('pagehide', () => { if (viewer && !viewer.isDestroyed()) viewer.destroy(); });
})();
