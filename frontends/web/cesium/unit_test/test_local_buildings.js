'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_buildings.js'),'utf8'),context);
const ring=[[0,0],[.00001,0],[.00001,.00001],[0,0]];
function fixture(buildings,height=1000){
  let cameraChanged,ground=10,removed=false;
  const entities=[];
  const color={withAlpha(){return this;}};
  const C={CustomDataSource:class {constructor(){this.entities={
    add:e=>{entities.push(e);return e;},remove:e=>entities.splice(entities.indexOf(e),1)};}},
    PolygonHierarchy:class {constructor(positions,holes=[]){this.positions=positions;this.holes=holes;}},
    Cartesian3:{fromRadians:(x,y)=>({x,y})},Color:{fromCssColorString:()=>color},Credit:class {}};
  const camera={positionCartographic:{height,longitude:0,latitude:0},
    moveEnd:{addEventListener(fn){cameraChanged=fn;return ()=>{cameraChanged=()=>{};};}}};
  const viewer={dataSources:{add(){},remove(){removed=true;}},cesiumWidget:{creditDisplay:{addStaticCredit(){}}},
    scene:{requestRender(){}},camera};
  const layer=context.window.ORCLocalBuildings(viewer,{buildings},C,()=>ground);
  return {entities,camera,layer,move:()=>cameraChanged(),setGround:value=>{ground=value;},get removed(){return removed;}};
}
function building(kind='osm-height',extra={}){return {ring_rad:ring,height_m:20,height_source:kind,...extra};}

test('courtyards and elevated parts retain bottom and top heights through terrain changes',()=>{
  const f=fixture([building('osm-height',{min_height_m:5,is_part:true,
    holes_rad:[[[.000006,.000001],[.000008,.000001],[.000008,.000002],[.000006,.000001]]]})]);
  const polygon=f.entities[0].polygon;
  assert.equal(polygon.height,15);assert.equal(polygon.extrudedHeight,30);
  assert.equal(polygon.hierarchy.holes.length,1);
  assert.equal(polygon.hierarchy.holes[0].positions.length,3);
  f.setGround(30);f.layer.refreshGround();
  assert.equal(polygon.height,35);assert.equal(polygon.extrudedHeight,50);
  f.camera.positionCartographic.height=20000;f.move();
  assert.equal(f.entities.length,0);
});

test('estimates appear close in and disappear without retained entities when zoomed out',()=>{
  const f=fixture([building(),building('levels-estimate'),building('placeholder')],10000);
  assert.equal(f.entities.length,1);
  f.camera.positionCartographic.height=2000;f.move();assert.equal(f.entities.length,2);
  f.camera.positionCartographic.height=1000;f.move();assert.equal(f.entities.length,3);
  assert.match(f.layer.label,/1 approximate/);
  f.camera.positionCartographic.longitude=.1;f.move();assert.equal(f.entities.length,2);
  f.camera.positionCartographic.height=10000;f.move();assert.equal(f.entities.length,1);
  f.layer.destroy();f.move();assert.equal(f.removed,true);
});

test('containing outline cannot occlude tower and wing parts',()=>{
  const f=fixture([building('osm-height',{height_m:76,outline_only:true}),
    building('osm-height',{height_m:76,is_part:true}),building('levels-estimate',{height_m:12,is_part:true})]);
  assert.equal(f.entities.length,2);
  assert.deepEqual(f.entities.map(e=>e.polygon.extrudedHeight),[86,22]);
});

test('dense residential tiles allocate at most 512 entities and prioritize height tags',()=>{
  const dense=Array.from({length:10000},()=>building('placeholder'));
  dense.push(building('osm-height',{height_m:76}));
  const f=fixture(dense);
  assert.equal(f.entities.length,512);
  assert.equal(f.entities[0].polygon.extrudedHeight,86);
  f.camera.positionCartographic.height=2000;f.move();assert.equal(f.entities.length,1);
});
