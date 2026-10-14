'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_buildings.js'),'utf8'),context);
test('building bases follow relief changes while building height remains real',()=>{
  let ground=10;
  const entities=[];
  let cameraHeight=1000;
  let cameraChanged;
  const color={withAlpha(){return this;}};
  const C={CustomDataSource:class {constructor(){this.entities={add:e=>{entities.push(e);return e;}};}},
    PolygonHierarchy:class {},Cartesian3:{fromRadians:(x,y)=>({x,y})},
    Color:{fromCssColorString:()=>color},Credit:class {}};
  const viewer={dataSources:{add(){},remove(){}},cesiumWidget:{creditDisplay:{addStaticCredit(){}}},scene:{requestRender(){}},
    camera:{positionCartographic:{get height(){return cameraHeight;}},changed:{addEventListener(fn){cameraChanged=fn;return ()=>{};}}}};
  const data={buildings:[{ring_rad:[[0,0],[1,0],[1,1],[0,0]],height_m:20,height_source:'osm-height'}]};
  const layer=context.window.ORCLocalBuildings(viewer,data,C,()=>ground);
  assert.equal(entities[0].polygon.height,10);
  ground=30;
  layer.refreshGround();
  assert.equal(entities[0].polygon.height,30);
  assert.equal(entities[0].polygon.extrudedHeight,50);
  ground=0;
  layer.refreshGround();
  assert.equal(entities[0].polygon.extrudedHeight,20);
  cameraHeight=20000;cameraChanged();
  assert.equal(entities[0].show,false);
});

test('building detail is distance-aware and generic placeholders stay hidden',()=>{
  let cameraHeight=10000;
  let changed;
  const entities=[];
  const color={withAlpha(){return this;}};
  const C={CustomDataSource:class {constructor(){this.entities={add:e=>{entities.push(e);return e;}};}},
    PolygonHierarchy:class {},Cartesian3:{fromRadians:(x,y)=>({x,y})},
    Color:{fromCssColorString:()=>color},Credit:class {}};
  const viewer={dataSources:{add(){},remove(){}},cesiumWidget:{creditDisplay:{addStaticCredit(){}}},scene:{requestRender(){}},
    camera:{positionCartographic:{get height(){return cameraHeight;}},changed:{addEventListener(fn){changed=fn;return ()=>{};}}}};
  const ring=[[0,0],[1,0],[1,1],[0,0]];
  context.window.ORCLocalBuildings(viewer,{buildings:[
    {ring_rad:ring,height_m:20,height_source:'osm-height'},
    {ring_rad:ring,height_m:12,height_source:'levels-estimate'},
    {ring_rad:ring,height_m:9,height_source:'placeholder'}]},C);
  assert.deepEqual(entities.map(e=>e.show),[true,false,false]);
  cameraHeight=2000;changed();
  assert.deepEqual(entities.map(e=>e.show),[true,true,false]);
});
