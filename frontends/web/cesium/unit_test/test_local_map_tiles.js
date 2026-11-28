'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const test = require('node:test');
const tick = () => new Promise(resolve=>setImmediate(resolve));

test('bounded loads discard stale completions, unload old geometry and clean up', async()=>{
  const pending=[];
  const layers=[];
  const sources=[];
  let rectangle={west:0,south:0,east:5,north:1};
  let listener;
  const color={withAlpha(){return this;}};
  const C={
    CustomDataSource:class {constructor(){this.entities={add(){}};this.show=true;}},
    Color:{TRANSPARENT:color,CYAN:color},Credit:class {},GridImageryProvider:class {},
    Rectangle:{fromRadians(west,south,east,north){return {west,south,east,north};},
      center(r){return {longitude:(r.west+r.east)/2,latitude:(r.south+r.north)/2};}},
    SingleTileImageryProvider:{fromUrl(url){return new Promise(resolve=>pending.push({url,resolve}));}}
  };
  const viewer={
    dataSources:{add(s){sources.push(s);},remove(s){const i=sources.indexOf(s);if(i>=0)sources.splice(i,1);}},
    imageryLayers:{addImageryProvider(p){layers.push(p);return p;},remove(p){const i=layers.indexOf(p);if(i>=0)layers.splice(i,1);}},
    cesiumWidget:{creditDisplay:{addStaticCredit(){}}},scene:{requestRender(){}},
    camera:{computeViewRectangle(){return rectangle;},moveEnd:{addEventListener(fn){listener=fn;return ()=>listener=null;}}}
  };
  const window={ORCLocalBuildings(){const source={show:true};viewer.dataSources.add(source);return {source};}};
  const context={window,AbortController,setTimeout,clearTimeout,Map,Set,document:{body:{classList:{contains:()=>false}},getElementById(){return {}; }},
    fetch:async()=>({ok:true,json:async()=>({buildings:[]})})};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_map_tiles.js'),'utf8'),context);
  const data={coverage:{west_rad:0,south_rad:0,east_rad:5,north_rad:1},tiles:
    Array.from({length:5},(_,i)=>({id:String(i),west_rad:i,east_rad:i+1,south_rad:0,north_rad:1,
      imagery_url:`/i${i}`,buildings_url:`/b${i}`,attribution:'test'}))};
  const map=window.ORCLocalMapTiles(viewer,data,C,undefined,true);
  map.update();await tick();
  assert.equal(pending.length,2,'Only two concurrent imagery loads');
  rectangle={west:4.1,south:0,east:4.9,north:1};
  map.update();
  for(const p of pending.splice(0))p.resolve({});
  await tick();
  assert.equal(layers.length,1,'Stale tiles never attach; only transparent base remains');
  assert.equal(pending.length,1);
  pending.shift().resolve({});await tick();
  assert.equal(layers.length,2);
  assert.equal(sources.length,2,'Coverage and one building source');
  map.show=false;
  assert.equal(sources[1].show,false);
  map.destroy();map.destroy();
  assert.equal(layers.length,0);
  assert.equal(sources.length,0);
  assert.equal(listener,null);
});

test('building-only packs attach without requesting imagery',async()=>{
  const sources=[];
  let images=0;
  const C={CustomDataSource:class{constructor(){this.entities={add(){}};this.show=true;}},
    Color:{TRANSPARENT:{},CYAN:{}},Credit:class{},
    Rectangle:{fromRadians(){return {};},center(){return {longitude:.5,latitude:.5};}},
    GridImageryProvider:class{constructor(){throw Error('Unexpected imagery base');}},
    SingleTileImageryProvider:{fromUrl(){images++;}}};
  const viewer={dataSources:{add(s){sources.push(s);},remove(s){sources.splice(sources.indexOf(s),1);}},
    imageryLayers:{addImageryProvider(){throw Error('Unexpected imagery');}},
    cesiumWidget:{creditDisplay:{addStaticCredit(){}}},scene:{requestRender(){}},
    camera:{computeViewRectangle(){return {west:0,south:0,east:1,north:1};},moveEnd:{addEventListener(){return ()=>{};}}}};
  const window={ORCLocalBuildings(){const source={show:true};viewer.dataSources.add(source);return {source};}};
  const readout={};
  const context={window,AbortController,setTimeout,clearTimeout,Map,Set,
    document:{body:{classList:{contains:()=>true}},getElementById(){return readout;}},fetch:async()=>({ok:true,json:async()=>({buildings:[]})})};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_map_tiles.js'),'utf8'),context);
  const data={coverage:{west_rad:0,south_rad:0,east_rad:1,north_rad:1},
    tiles:[{id:'a',west_rad:0,south_rad:0,east_rad:1,north_rad:1,imagery_url:null,buildings_url:'/b'}]};
  const map=window.ORCLocalMapTiles(viewer,data,C,undefined,false);
  map.update();await tick();
  assert.equal(images,0);
  assert.equal(sources[1].show,false);
  assert.match(readout.textContent,/Tiles 1\/1 active/);
  assert.equal(readout.hidden,true,'Normal tile diagnostics do not cover an embedded map');
  map.destroy();
  assert.equal(sources.length,0);
  context.fetch=async()=>({ok:false});
  const failed=window.ORCLocalMapTiles(viewer,data,C,undefined,false);
  failed.update();await tick();
  assert.match(readout.textContent,/Tile unavailable:/);
  assert.equal(readout.hidden,false,'Load errors stay visible in embedded mode');
  failed.destroy();
});

test('horizon tilt keeps ground-focused tiles and uses lower visible ground when center is sky',async()=>{
  let view={west:0,south:0,east:.04,north:1};
  let centerIsSky=false;
  const loaded=[],destroyed=[],fractions=[];
  const sources=[];
  const C={CustomDataSource:class{constructor(){this.entities={add(){}};this.show=true;}},
    Color:{TRANSPARENT:{},CYAN:{}},Credit:class{},
    Cartographic:{fromCartesian:point=>point},
    Rectangle:{fromRadians(){return {};},center:r=>({longitude:(r.west+r.east)/2,latitude:.5})}};
  const viewer={dataSources:{add(s){sources.push(s);},remove(s){sources.splice(sources.indexOf(s),1);}},
    cesiumWidget:{creditDisplay:{addStaticCredit(){}}},scene:{requestRender(){}},
    camera:{computeViewRectangle:()=>view,positionCartographic:{longitude:0,latitude:.5},
      moveEnd:{addEventListener(){return ()=>{};}}}};
  const window={ORCCameraGroundAnchor(_viewer,_C,fraction=.5){
    fractions.push(fraction);
    return centerIsSky && fraction===.5 ? undefined : {longitude:.005,latitude:.5};
  },ORCLocalBuildings(_viewer,data){
    loaded.push(data.id);
    const source={show:true};
    return {source,destroy(){destroyed.push(data.id);}};
  }};
  const context={window,AbortController,setTimeout,clearTimeout,Map,Set,
    document:{body:{classList:{contains:()=>false}},getElementById(){return {};}},
    fetch:async url=>({ok:true,json:async()=>({id:url})})};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_map_tiles.js'),'utf8'),context);
  const tiles=Array.from({length:8},(_,i)=>{
    const west=i<4 ? i*.01 : .5+(i-4)*.01;
    return {id:String(i),west_rad:west,east_rad:west+.01,south_rad:0,north_rad:1,
      imagery_url:null,buildings_url:'/b'+i};
  });
  const map=window.ORCLocalMapTiles(viewer,{coverage:{},tiles},C,undefined,true);
  map.update();await tick();
  assert.deepEqual(loaded,['/b0','/b1','/b2','/b3']);
  view={west:0,south:0,east:1.2,north:1};
  centerIsSky=true;fractions.length=0;
  map.update();await tick();
  assert.deepEqual(fractions,[.5,.75]);
  assert.deepEqual(loaded,['/b0','/b1','/b2','/b3']);
  assert.equal(destroyed.length,0,'Tilting must not evict nearby geometry for horizon tiles');
  map.destroy();
  assert.equal(destroyed.length,4);
  // Adaptive cells can have distant centroids despite containing the focus.
  loaded.length=0;centerIsSky=false;view={west:-1,south:0,east:1,north:1};
  const adaptive=Array.from({length:4},(_,i)=>({id:'s'+i,west_rad:-(i+1)*.004,
    east_rad:-i*.004,south_rad:0,north_rad:1,imagery_url:null,buildings_url:'/s'+i}));
  adaptive.push({id:'big',west_rad:0,east_rad:1,south_rad:0,north_rad:1,
    imagery_url:null,buildings_url:'/big'});
  const other=window.ORCLocalMapTiles(viewer,{coverage:{},tiles:adaptive},C,undefined,true);
  other.update();await tick();
  assert.equal(loaded.length,4);
  assert.ok(loaded.includes('/big'),'The containing tile wins over closer neighboring centroids');
  other.destroy();
});
