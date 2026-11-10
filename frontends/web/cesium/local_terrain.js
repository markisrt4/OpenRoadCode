/* Local relief with bounded detail paging; never absolute-height conversion. */
'use strict';
window.ORCLocalTerrain = function (data, C, initialPoint=null) {
  let scale = 1;
  let visible = true;
  const scheme = new C.GeographicTilingScheme();
  const rank=(a,b)=>(b.detail_level||0)-(a.detail_level||0)
    || ((a.east_rad-a.west_rad)*(a.north_rad-a.south_rad)/((a.width-1)*(a.height-1))
      -(b.east_rad-b.west_rad)*(b.north_rad-b.south_rad)/((b.width-1)*(b.height-1)));
  const baseline=(data.tiles || [data]).slice().sort(rank);
  let tiles=baseline.slice();
  const pages=new Map();
  const pendingPages=new Map();
  let detailEntries=new Map();
  async function loadPage(x,y,level){
    if(!data.page_url || level<12)return;
    const key=`${level}/${x}/${y}`;
    if(pages.has(key)){
      const value=pages.get(key);pages.delete(key);pages.set(key,value);return;
    }
    if(pendingPages.has(key))return pendingPages.get(key);
    const url=data.page_url.replace('{z}',level).replace('{x}',x).replace('{y}',y);
    const request=fetch(url).then(response=>{
      if(!response.ok)throw Error('Offline terrain detail page unavailable');
      return response.json();
    }).then(page=>{
      if(!Array.isArray(page.tiles)||page.tiles.length>64)throw Error('Invalid terrain detail page');
      pages.set(key,page.tiles);
      while(pages.size>4)pages.delete(pages.keys().next().value);
      const retained=new Map();
      for(const docs of pages.values())for(const doc of docs){
        if(typeof doc.id!=='string'||!doc.url)throw Error('Invalid terrain detail entry');
        retained.set(doc.id,detailEntries.get(doc.id)||doc);
      }
      detailEntries=retained;tiles=[...detailEntries.values(),...baseline].sort(rank);
    }).finally(()=>pendingPages.delete(key));
    pendingPages.set(key,request);return request;
  }
  async function loadTile(tile) {
    if(tile.heights_m)return tile;
    if(!tile.pending)tile.pending=fetch(tile.url).then(response=>{
      if(!response.ok)throw Error('Offline terrain tile unavailable');
      return response.json();
    }).then(payload=>{
      if(payload.width!==tile.width||payload.height!==tile.height||
          !Array.isArray(payload.heights_m)||payload.heights_m.length!==tile.width*tile.height)
        throw Error('Offline terrain tile is invalid');
      tile.heights_m=payload.heights_m;
      return tile;
    });
    return tile.pending;
  }
  function tileAt(longitude,latitude,zoom=Infinity,catalog=tiles) {
    return catalog.find(item=>(item.minimum_zoom||0)<=zoom
      && longitude>=item.west_rad&&longitude<=item.east_rad
      && latitude>=item.south_rad&&latitude<=item.north_rad);
  }
  async function loadAt(longitude,latitude,zoom=Infinity) {
    const tile=tileAt(longitude,latitude,zoom);
    return tile ? loadTile(tile) : null;
  }
  const ready=initialPoint?loadAt(initialPoint[0],initialPoint[1]):Promise.resolve();
  function sample(tile,longitude,latitude) {
    const x = (longitude-tile.west_rad)/(tile.east_rad-tile.west_rad)*(tile.width-1);
    const y = (tile.north_rad-latitude)/(tile.north_rad-tile.south_rad)*(tile.height-1);
    const col = Math.min(Math.floor(x),tile.width-2), row = Math.min(Math.floor(y),tile.height-2);
    const fx=x-col, fy=y-row;
    const at = (r,c) => tile.heights_m[r*tile.width+c]-tile.reference_height_m;
    const value=(at(row,col)*(1-fx)+at(row,col+1)*fx)*(1-fy)+
      (at(row+1,col)*(1-fx)+at(row+1,col+1)*fx)*fy;
    // Fade the boundary to the zero-relief outside region to avoid vertical seams.
    // A single pack fades at its outer boundary. Mosaic tile edges stay continuous.
    const margin = !data.page_url && tiles.length === 1 ? Math.min(x,y,tile.width-1-x,tile.height-1-y) : 1;
    return scale*value*Math.min(1,Math.max(0,margin));
  }
  function sampledHeightAt(longitude, latitude, zoom=Infinity,catalog=tiles) {
    const tile = catalog.find(item => item.heights_m && (item.minimum_zoom||0)<=zoom
      && longitude>=item.west_rad && longitude<=item.east_rad
      && latitude>=item.south_rad && latitude<=item.north_rad);
    return tile ? sample(tile,longitude,latitude) : 0;
  }
  function heightAt(longitude, latitude) {
    return visible ? sampledHeightAt(longitude, latitude) : 0;
  }
  function createProvider() {
    const provider = new C.CustomHeightmapTerrainProvider({width:33,height:33,tilingScheme:scheme,
      credit:data.attribution,
      callback:async (x,y,level) => {
        await loadPage(x,y,level);
        const catalog=tiles.slice();
        const rectangle=scheme.tileXYToRectangle(x,y,level);
        const wanted=new Set();
        for(let row=0;row<33;row++)for(let col=0;col<33;col++){
          const tile=tileAt(rectangle.west+(rectangle.east-rectangle.west)*col/32,
            rectangle.north-(rectangle.north-rectangle.south)*row/32,level,catalog);
          if(tile)wanted.add(tile);
        }
        await Promise.all([...wanted].map(loadTile));
        const buffer=new Float32Array(33*33);
        for (let row=0;row<33;row++) for (let col=0;col<33;col++) {
          buffer[row*33+col]=sampledHeightAt(rectangle.west+(rectangle.east-rectangle.west)*col/32,
            rectangle.north-(rectangle.north-rectangle.south)*row/32,level,catalog);
        }
        return buffer;
      }
    });
    const geometricError=provider.getLevelMaximumGeometricError.bind(provider);
    // Do not keep subdividing a ~100 m source grid into metre-scale meshes.
    const maximumZoom=data.maximum_zoom||13;
    // Coarse globe meshes can otherwise step completely over a narrow regional
    // pack. Keep enough refinement pressure for statewide relief to contribute
    // vertices before the camera reaches street scale.
    provider.getLevelMaximumGeometricError=level => level>=maximumZoom ? 0 :
      geometricError(level)*(level<6?4:1);
    return provider;
  }
  let provider = createProvider();
  const flat = new C.EllipsoidTerrainProvider();
  function setVisible(viewer, value) {
    visible = value;
    viewer.terrainProvider = visible ? provider : flat;
    viewer.scene.requestRender();
  }
  function setScale(viewer, value) {
    if (![1,2,3,4].includes(value)) throw new Error('Terrain scale must be 1, 2, 3 or 4');
    if (scale === value) return;
    scale = value;
    // Replacing the provider invalidates already generated terrain meshes.
    provider = createProvider();
    viewer.terrainProvider = visible ? provider : flat;
    viewer.scene.requestRender();
  }
  return {get provider(){return provider;},heightAt,setVisible,setScale,loadTile,ready,
    get sourceReliefM(){
      let minimum=Infinity,maximum=-Infinity;
      for(const tile of tiles)for(const height of tile.heights_m||[]){minimum=Math.min(minimum,height);maximum=Math.max(maximum,height);}
      return Number.isFinite(minimum)?maximum-minimum:0;
    }};
};
