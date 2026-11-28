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
  const meshes=new Map(),pendingMeshes=new Map();
  let detailEntries=new Map();
  async function loadPage(x,y,level){
    if(!data.page_url || level<(data.page_minimum_zoom??12))return [];
    const key=`${level}/${x}/${y}`;
    if(pages.has(key)){
      const value=pages.get(key);pages.delete(key);pages.set(key,value);
      return value.map(doc=>detailEntries.get(doc.tile_id??doc.id)||doc);
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
        const identity=doc.tile_id??doc.id;
        if(typeof identity!=='string'||!doc.url)throw Error('Invalid terrain detail entry');
        retained.set(identity,detailEntries.get(identity)||doc);
      }
      detailEntries=retained;tiles=[...detailEntries.values(),...baseline].sort(rank);
      // Return strong references to this request's page. Other requests may
      // evict it from the global LRU before this callback starts sampling.
      return page.tiles.map(doc=>retained.get(doc.tile_id??doc.id)||doc);
    }).finally(()=>pendingPages.delete(key));
    pendingPages.set(key,request);return request;
  }
  async function requestMesh(x,y,level){
    const key=`${level}/${x}/${y}`;
    if(meshes.has(key)){const value=meshes.get(key);meshes.delete(key);meshes.set(key,value);return value;}
    if(pendingMeshes.has(key))return pendingMeshes.get(key);
    const url=data.mesh_url.replace('{z}',level).replace('{x}',x).replace('{y}',y);
    const pending=fetch(url).then(response=>{
      if(!response.ok)throw Error('Offline terrain mesh unavailable');
      return response.json();
    }).then(payload=>{
      if(payload.width!==33||payload.height!==33||!Array.isArray(payload.heights_m)
        ||payload.heights_m.length!==1089||!payload.heights_m.every(Number.isFinite)
        ||!Number.isFinite(payload.reference_height_m))throw Error('Invalid offline terrain mesh');
      const rectangle=scheme.tileXYToRectangle(x,y,level);
      const mesh={...payload,west_rad:rectangle.west,south_rad:rectangle.south,
        east_rad:rectangle.east,north_rad:rectangle.north,mesh:true};
      meshes.set(key,mesh);while(meshes.size>8)meshes.delete(meshes.keys().next().value);
      return mesh;
    }).finally(()=>pendingMeshes.delete(key));
    pendingMeshes.set(key,pending);return pending;
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
  const ready=initialPoint&&data.mesh_url?requestMesh(
    Math.min(2**13-1,Math.max(0,Math.floor((initialPoint[0]+Math.PI)/(2*Math.PI)*2**13))),
    Math.min(2**12-1,Math.max(0,Math.floor((Math.PI/2-initialPoint[1])/Math.PI*2**12))),12)
    :initialPoint?loadAt(initialPoint[0],initialPoint[1]):Promise.resolve();
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
    const margin = !tile.mesh && !data.page_url && tiles.length === 1 ? Math.min(x,y,tile.width-1-x,tile.height-1-y) : 1;
    return scale*value*Math.min(1,Math.max(0,margin));
  }
  function sampledHeightAt(longitude, latitude, zoom=Infinity,catalog=tiles) {
    const available=catalog.filter(item=>item.heights_m && (item.minimum_zoom||0)<=zoom
      && longitude>=item.west_rad && longitude<=item.east_rad
      && latitude>=item.south_rad && latitude<=item.north_rad);
    if(!available.length)return 0;
    const evaluate=index=>{
      const tile=available[index];
      const value=sample(tile,longitude,latitude);
      if(!data.page_url)return value;
      const dx=(tile.east_rad-tile.west_rad)/(tile.width-1);
      const dy=(tile.north_rad-tile.south_rad)/(tile.height-1);
      const area=dx*dy;
      let weight=1;
      const band=Math.min(2,(tile.width-1)*.1,(tile.height-1)*.1);
      const probes=[[(longitude-tile.west_rad)/dx,tile.west_rad-dx*.01,latitude],
        [(tile.east_rad-longitude)/dx,tile.east_rad+dx*.01,latitude],
        [(latitude-tile.south_rad)/dy,longitude,tile.south_rad-dy*.01],
        [(tile.north_rad-latitude)/dy,longitude,tile.north_rad+dy*.01]];
      for(const [distance,x,y] of probes){
        if(distance>=band)continue;
        const neighbor=catalog.some(other=>other!==tile && (other.minimum_zoom||0)<=zoom
          && (other.detail_level||0)>=(tile.detail_level||0)
          && (other.east_rad-other.west_rad)*(other.north_rad-other.south_rad)/((other.width-1)*(other.height-1))<=area*1.1
          && x>=other.west_rad && x<=other.east_rad && y>=other.south_rad && y<=other.north_rad);
        if(!neighbor)weight=Math.min(weight,Math.max(0,distance/band));
      }
      // Only exposed edges fade; shared fine-grid edges stay at source height.
      // Raw elevations are untouched. Blend into the next available coarse grid.
      if(weight>=1)return value;
      const t=weight*weight*(3-2*weight);
      const fallback=available.findIndex((other,next)=>next>index && ((other.detail_level||0)<(tile.detail_level||0)
        || (other.east_rad-other.west_rad)*(other.north_rad-other.south_rad)/((other.width-1)*(other.height-1))>area*1.1));
      const lower=fallback>=0?evaluate(fallback):0;
      return lower+(value-lower)*t;
    };
    return evaluate(0);
  }
  function heightAt(longitude, latitude) {
    if(data.mesh_url){
      if(!visible)return 0;
      const matching=[...meshes.values()].filter(mesh=>longitude>=mesh.west_rad&&longitude<=mesh.east_rad
        &&latitude>=mesh.south_rad&&latitude<=mesh.north_rad).sort((a,b)=>
          (a.east_rad-a.west_rad)*(a.north_rad-a.south_rad)-(b.east_rad-b.west_rad)*(b.north_rad-b.south_rad));
      return matching.length?sample(matching[0],longitude,latitude):0;
    }
    return visible ? sampledHeightAt(longitude, latitude) : 0;
  }
  function createProvider() {
    const provider = new C.CustomHeightmapTerrainProvider({width:33,height:33,tilingScheme:scheme,
      credit:data.attribution,
      callback:(x,y,level) => {
        if(data.mesh_url){
          const key=`${level}/${x}/${y}`;
          // CustomHeightmapTerrainProvider retries an undefined return. Bound
          // CPU/file work and leave localhost connections free for imagery.
          if(pendingMeshes.size>=4&&!pendingMeshes.has(key)&&!meshes.has(key))return undefined;
          return requestMesh(x,y,level).then(mesh=>
            Float32Array.from(mesh.heights_m,height=>scale*(height-mesh.reference_height_m)));

        }
        return (async()=>{
        const ownPage=await loadPage(x,y,level);
        const rectangle=scheme.tileXYToRectangle(x,y,level);
        const catalog=[...ownPage,...baseline].filter(tile=>tile.west_rad<=rectangle.east
          && tile.east_rad>=rectangle.west && tile.south_rad<=rectangle.north
          && tile.north_rad>=rectangle.south).sort(rank);
        const wanted=new Set();
        for(let row=0;row<33;row++)for(let col=0;col<33;col++){
          const longitude=rectangle.west+(rectangle.east-rectangle.west)*col/32;
          const latitude=rectangle.north-(rectangle.north-rectangle.south)*row/32;
          for(const tile of catalog)if((tile.minimum_zoom||0)<=level && longitude>=tile.west_rad
            && longitude<=tile.east_rad && latitude>=tile.south_rad && latitude<=tile.north_rad)wanted.add(tile);
        }
        await Promise.all([...wanted].map(loadTile));
        const buffer=new Float32Array(33*33);
        for (let row=0;row<33;row++) for (let col=0;col<33;col++) {
          buffer[row*33+col]=sampledHeightAt(rectangle.west+(rectangle.east-rectangle.west)*col/32,
            rectangle.north-(rectangle.north-rectangle.south)*row/32,level,catalog);
        }
        return buffer;
        })();
      }
    });
    const geometricError=provider.getLevelMaximumGeometricError.bind(provider);
    // Do not keep subdividing a ~100 m source grid into metre-scale meshes.
    const maximumZoom=data.maximum_zoom||13;
    // Coarse globe meshes can otherwise step completely over a narrow regional
    // pack. Keep enough refinement pressure for statewide relief to contribute
    // vertices before the camera reaches street scale.
    provider.getLevelMaximumGeometricError=level => level>=maximumZoom ? 0 :
      geometricError(level)*scale*(level<6?4:1);
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
      for(const tile of data.mesh_url?meshes.values():tiles)for(const height of tile.heights_m||[]){minimum=Math.min(minimum,height);maximum=Math.max(maximum,height);}
      return Number.isFinite(minimum)?maximum-minimum:0;
    }};
};
