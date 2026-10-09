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
  const context={window,AbortController,setTimeout,clearTimeout,Map,Set,document:{getElementById(){return {}; }},
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
