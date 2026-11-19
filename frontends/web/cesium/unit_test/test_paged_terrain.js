'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
function fixture(minimumZoom=12,semanticId=false,distinctPages=false,neighbor=false){
  const calls=[];
  const base={west_rad:0,south_rad:0,east_rad:1,north_rad:1,width:2,height:2,
    heights_m:[10,10,10,10],reference_height_m:10,detail_level:0};
  const context={window:{},fetch:async url=>{
    calls.push(url);
    if(url.startsWith('/page/')){
      const x=distinctPages?Number(url.split('/')[3]):0;
      const doc={...base,west_rad:x,east_rad:x+1,heights_m:undefined,
        ...(semanticId?{tile_id:url}:{id:url}),url:'/chunk/'+url,detail_level:7,minimum_zoom:minimumZoom};
      const docs=[doc];
      if(neighbor)docs.push({...doc,west_rad:1,east_rad:2,id:'neighbor',tile_id:'neighbor',url:'/chunk/neighbor'});
      return {ok:true,json:async()=>({tiles:docs})};
    }
    return {ok:true,json:async()=>({width:2,height:2,heights_m:[40,40,40,40]})};
  }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_terrain.js'),'utf8'),context);
  const C={GeographicTilingScheme:class {tileXYToRectangle(x){return {west:distinctPages?x:0,south:0,east:distinctPages?x+1:1,north:1};}},
    CustomHeightmapTerrainProvider:class {constructor(options){this.callback=options.callback;}getLevelMaximumGeometricError(){return 1;}},
    EllipsoidTerrainProvider:class {}};
  const layer=context.window.ORCLocalTerrain({tiles:[base],page_url:'/page/{z}/{x}/{y}',page_minimum_zoom:minimumZoom,maximum_zoom:16},C);
  return {layer,calls,C};
}

test('fine pages override the baseline, reuse payloads, and evict old pages',async()=>{
  const {layer,calls}=fixture();
  assert.equal((await layer.provider.callback(0,0,11))[0],0);
  assert.equal(calls.length,0);
  assert.equal((await layer.provider.callback(0,0,12))[16*33+16],30);
  await layer.provider.callback(0,0,12);assert.equal(calls.length,2);
  for(let x=1;x<=4;x++)await layer.provider.callback(x,0,12);
  await layer.provider.callback(0,0,12);
  assert.equal(calls.filter(url=>url==='/page/12/0/0').length,2);
  assert.equal(layer.heightAt(.5,.5),30);
});

test('loading cached data after hiding cannot reactivate terrain',async()=>{
  const {layer,C}=fixture();
  const old=layer.provider;const pending=old.callback(0,0,12);
  const viewer={scene:{requestRender(){}}};layer.setVisible(viewer,false);
  await pending;
  assert.ok(viewer.terrainProvider instanceof C.EllipsoidTerrainProvider);
  assert.equal(layer.heightAt(.5,.5),0);
});


test('national terrain pages start at their declared coarse zoom',async()=>{
  const {layer,calls}=fixture(8,true);
  assert.equal((await layer.provider.callback(0,0,7))[0],0);
  assert.equal(calls.length,0);
  assert.equal((await layer.provider.callback(0,0,8))[16*33+16],30);
  assert.ok(calls.includes('/page/8/0/0'));
});


test('each concurrent mesh keeps its own page after the global LRU evicts it',async()=>{
  const {layer,calls}=fixture(8,true,true);
  const buffers=await Promise.all(Array.from({length:8},(_,x)=>layer.provider.callback(x,0,8)));
  assert.equal(calls.filter(url=>url.startsWith('/page/')).length,8);
  for(const buffer of buffers)assert.equal(buffer[16*33+16],30);
});

test('detail edges meet coarse coverage smoothly rather than forming a wall',async()=>{
  const {layer}=fixture(8,true);
  const buffer=await layer.provider.callback(0,0,8);
  assert.equal(buffer[0],0);
  assert.equal(buffer[16*33+16],30);
  assert.ok(buffer[16*33+1]>0&&buffer[16*33+1]<30);
});


test('shared fine-grid edges retain source height instead of fading into a trench',async()=>{
  const {layer}=fixture(8,true,false,true);
  const buffer=await layer.provider.callback(0,0,8);
  assert.equal(buffer[16*33+32],30);
});
