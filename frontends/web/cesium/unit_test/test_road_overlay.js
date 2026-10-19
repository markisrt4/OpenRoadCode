'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
test('road overlay bounds requests, labels roads and places, and prevents attachment after close',async()=>{
  const sources=[];let render;const pending=[];
  const color={withAlpha(){return this;}};
  const C={Cartesian2:class {},DistanceDisplayCondition:class {constructor(near,far){this.near=near;this.far=far;}},Cartographic:{fromCartesian:point=>point},
    Cartesian3:{fromRadians:(...point)=>point,fromRadiansArray:point=>point},
    Color:{WHITE:color,BLACK:color,fromCssColorString:()=>color},LabelStyle:{FILL_AND_OUTLINE:1},Credit:class {},
    CustomDataSource:class {constructor(){this.entities={values:[],add(value){this.values.push(value);return value;}};}}};
  const viewer={camera:{getPickRay:()=>({}),positionCartographic:{height:1000}},
    scene:{canvas:{clientWidth:600,clientHeight:400},globe:{pick:()=>({longitude:-1.4,latitude:.7})},
      requestRender(){},postRender:{addEventListener(callback){render=callback;return()=>{render=null;};}}},
    cesiumWidget:{creditDisplay:{addStaticCredit(){}}},dataSources:{async add(source){sources.push(source);return source;},
      remove(source){const index=sources.indexOf(source);if(index>=0)sources.splice(index,1);}}};
  const state={roads:[{kind:'motorway',label:'I-75',points:[[-1.4,.7],[-1.41,.71]]},{kind:'minor',label:'Main Street',points:[[-1.42,.7],[-1.43,.71]]}],places:[{name:'Detroit',position:[-1.4,.7]}]};
  const requested=[];
  const context={window:{},Date:{now:()=>1000},AbortController,requested,
    fetch:url=>{requested.push(url);return new Promise(resolve=>pending.push(resolve));}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../road_overlay.js'),'utf8'),context);
  const overlay=context.window.ORCRoadOverlay(viewer,C);
  render();assert.equal(pending.length,4);
  assert.ok(pending.length && context.requested.every(url=>url.startsWith('/data/roads/13/')));
  pending.shift()({ok:true,json:async()=>state});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(sources.length,1);
  assert.equal(sources[0].entities.values[1].label.text,'I-75');
  assert.equal(sources[0].entities.values[2].label.text,'Main Street');
  assert.equal(sources[0].entities.values[2].label.distanceDisplayCondition.far,1000);
  assert.equal(sources[0].entities.values.filter(entity=>entity.polyline).length,1,
    'local streets do not create extra ground-clamped geometry');
  assert.equal(sources[0].entities.values[1].label.distanceDisplayCondition,undefined);
  overlay.roadsVisible=false;assert.equal(sources[0].show,false);
  overlay.placesVisible=true;
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(sources.length,2);assert.equal(sources[1].entities.values[0].label.text,'Detroit');
  assert.equal(sources[1].show,true);
  overlay.destroy();
  pending.forEach(resolve=>resolve({ok:true,json:async()=>state}));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(sources.length,0);assert.equal(render,null);
});
