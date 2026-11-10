'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
function fixture(){
  const calls=[];
  const base={west_rad:0,south_rad:0,east_rad:1,north_rad:1,width:2,height:2,
    heights_m:[10,10,10,10],reference_height_m:10,detail_level:0};
  const context={window:{},fetch:async url=>{
    calls.push(url);
    if(url.startsWith('/page/'))return {ok:true,json:async()=>({tiles:[{
      ...base,heights_m:undefined,id:url,url:'/chunk/'+url,detail_level:7,minimum_zoom:12}]})};
    return {ok:true,json:async()=>({width:2,height:2,heights_m:[40,40,40,40]})};
  }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_terrain.js'),'utf8'),context);
  const C={GeographicTilingScheme:class {tileXYToRectangle(){return {west:0,south:0,east:1,north:1};}},
    CustomHeightmapTerrainProvider:class {constructor(options){this.callback=options.callback;}getLevelMaximumGeometricError(){return 1;}},
    EllipsoidTerrainProvider:class {}};
  const layer=context.window.ORCLocalTerrain({tiles:[base],page_url:'/page/{z}/{x}/{y}',maximum_zoom:16},C);
  return {layer,calls,C};
}

test('fine pages override the baseline, reuse payloads, and evict old pages',async()=>{
  const {layer,calls}=fixture();
  assert.equal((await layer.provider.callback(0,0,11))[0],0);
  assert.equal(calls.length,0);
  assert.equal((await layer.provider.callback(0,0,12))[0],30);
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
