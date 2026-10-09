/* Local presentation streaming: at most four attached tiles, two pending loads. */
'use strict';
window.ORCLocalMapTiles = function(viewer, data, C, heightAt, buildingsVisible) {
  const entries = new Map();
  let wanted = new Set();
  let disposed = false;
  let running = 0;
  let show = buildingsVisible;
  let timer;
  const readout = document.getElementById('tiles-status');
  const bounds = data.coverage;
  const coverageSource = new C.CustomDataSource('offline-coverage');
  viewer.dataSources.add(coverageSource);
  const rectangle = C.Rectangle.fromRadians(bounds.west_rad,bounds.south_rad,bounds.east_rad,bounds.north_rad);
  coverageSource.entities.add({rectangle:{coordinates:rectangle,
    material:C.Color.TRANSPARENT, outline:true,outlineColor:C.Color.CYAN, height:5}});
  viewer.cesiumWidget.creditDisplay.addStaticCredit(new C.Credit(
    '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · ODbL 1.0 · USGS / USDA NAIP',true));
  // First imagery layer must be global, to avoid stretching a bounded tile.
  const base = viewer.imageryLayers.addImageryProvider(new C.GridImageryProvider({
    color:C.Color.TRANSPARENT,glowColor:C.Color.TRANSPARENT,backgroundColor:C.Color.TRANSPARENT,cells:1}));
  function report(message) {
    if (disposed) return;
    const attached = [...entries.values()].filter(e=>e.layer).length;
    readout.textContent = message || `Tiles ${attached}/${wanted.size} active · ${data.tiles.length} installed`;
  }
  function remove(entry) {
    entry.abort.abort();
    if (entry.layer) viewer.imageryLayers.remove(entry.layer,true);
    if (entry.buildings) viewer.dataSources.remove(entry.buildings.source,true);
  }
  async function load(entry) {
    running++;
    try {
      const tile = entry.tile;
      const response = await fetch(tile.buildings_url,{signal:entry.abort.signal});
      if (!response.ok) throw new Error('Local building tile unavailable');
      const geometry = await response.json();
      if (disposed || !wanted.has(tile.id)) return;
      const provider = await C.SingleTileImageryProvider.fromUrl(tile.imagery_url,{
        rectangle:C.Rectangle.fromRadians(tile.west_rad,tile.south_rad,tile.east_rad,tile.north_rad),
        credit:tile.attribution});
      if (disposed || !wanted.has(tile.id) || entries.get(tile.id)!==entry) return;
      entry.layer = viewer.imageryLayers.addImageryProvider(provider);
      entry.buildings = window.ORCLocalBuildings(viewer,geometry,C,heightAt);
      entry.buildings.source.show = show;
      viewer.scene.requestRender();
    } catch(error) {
      if (!disposed && error.name !== 'AbortError' && wanted.has(entry.tile.id)) {
        entry.failed = true;
        report('Tile unavailable: '+error.message+' · move away and back to retry');
      }
    } finally {
      running--;
      if (!entry.failed) report();
      pump();
    }
  }
  function pump() {
    if (disposed) return;
    for (const tile of data.tiles) {
      if (running >= 2) break;
      if (wanted.has(tile.id) && !entries.has(tile.id)) {
        const entry = {tile,abort:new AbortController()};
        entries.set(tile.id,entry);
        load(entry);
      }
    }
  }
  function update() {
    if (disposed) return;
    const view = viewer.camera.computeViewRectangle();
    const center = view ? C.Rectangle.center(view) : viewer.camera.positionCartographic;
    const candidates = data.tiles.filter(tile => !view || (
      tile.west_rad <= view.east && tile.east_rad >= view.west &&
      tile.south_rad <= view.north && tile.north_rad >= view.south));
    const score = tile => Math.hypot(((tile.west_rad+tile.east_rad)/2-center.longitude)*Math.cos(center.latitude),
                                     (tile.south_rad+tile.north_rad)/2-center.latitude);
    candidates.sort((a,b)=>score(a)-score(b));
    wanted = new Set(candidates.slice(0,4).map(tile=>tile.id));
    for (const [id,entry] of entries) if (!wanted.has(id)) {remove(entry);entries.delete(id);}
    report(candidates.length>4 ? 'Detail limited to 4 nearby tiles · zoom in for complete local detail' : undefined);
    pump();
    viewer.scene.requestRender();
  }
  const unbind = viewer.camera.moveEnd.addEventListener(()=>{
    clearTimeout(timer);
    timer = setTimeout(update,250);
  });
  return {
    get show() {return show;},
    set show(value) {
      show = value;
      for (const entry of entries.values()) if (entry.buildings) entry.buildings.source.show=value;
      viewer.scene.requestRender();
    },
    update,
    destroy() {
      if (disposed) return;
      disposed=true;
      clearTimeout(timer);
      unbind();
      for (const entry of entries.values()) remove(entry);
      entries.clear();
      viewer.imageryLayers.remove(base,true);
      viewer.dataSources.remove(coverageSource,true);
    }
  };
};
