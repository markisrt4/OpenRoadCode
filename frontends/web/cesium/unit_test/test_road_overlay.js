'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
test('road overlay bounds requests, labels roads and places, and prevents attachment after close',async()=>{
  const sources=[];let render;const pending=[];let now=1000;
  const color={withAlpha(){return this;}};
  const C={Cartesian2:class {},Cartographic:{fromCartesian:point=>point},
    Cartesian3:{fromRadians:(...point)=>point,fromRadiansArray:point=>point,distance:(camera,point)=>camera.distance},
    SceneTransforms:{worldToWindowCoordinates:(scene,point)=>({x:point[0]<-1.415?400:200,y:200})},
    Color:{WHITE:color,BLACK:color,fromCssColorString:()=>color},LabelStyle:{FILL_AND_OUTLINE:1},Credit:class {},
    CustomDataSource:class {constructor(){this.entities={values:[],add(value){if(value.position){const world=value.position;value.position={getValue:()=>world};}this.values.push(value);return value;}};}}};
  const viewer={clock:{currentTime:0},camera:{getPickRay:()=>({}),positionCartographic:{height:1000},positionWC:{distance:2000}},
    scene:{canvas:{clientWidth:600,clientHeight:400},globe:{pick:()=>({longitude:-1.4,latitude:.7})},
      requestRender(){},postRender:{addEventListener(callback){render=callback;return()=>{render=null;};}}},
    cesiumWidget:{creditDisplay:{addStaticCredit(){}}},dataSources:{async add(source){sources.push(source);return source;},
      remove(source){const index=sources.indexOf(source);if(index>=0)sources.splice(index,1);}}};
  const state={roads:[{kind:'motorway',label:'I-75',points:[[-1.4,.7],[-1.41,.71]]},{kind:'minor',label:'Main Street',points:[[-1.42,.7],[-1.43,.71]]}],places:[{name:'Detroit',position:[-1.4,.7]}]};
  const context={window:{},Date:{now:()=>now},AbortController,
    fetch:()=>new Promise(resolve=>pending.push(resolve))};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../road_overlay.js'),'utf8'),context);
  const overlay=context.window.ORCRoadOverlay(viewer,C);
  render();assert.equal(pending.length,9);
  pending.shift()({ok:true,json:async()=>state});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(sources.length,1);
  assert.equal(sources[0].entities.values[1].label.text,'I-75');
  const labels=sources[0].entities.values.filter(entity=>entity.label);
  const street=labels.find(entity=>entity.label.text==='Main Street');
  const city=labels.find(entity=>entity.label.text==='Detroit');
  const freeway=labels.find(entity=>entity.label.text==='I-75');
  assert.equal(city.label.show,true);
  assert.equal(freeway.label.show,false,'city wins overlapping screen space');
  assert.equal(street.label.show,false,'streets hidden at wide viewing distance');
  viewer.camera.positionWC.distance=500;now+=200;render();
  assert.equal(street.label.show,true,'street appears when zoomed in');
  viewer.camera.positionWC.distance=2000;now+=200;render();
  assert.equal(street.label.show,false,'street hides when zooming out without reloading tile');
  overlay.show=false;assert.equal(sources[0].show,false);
  overlay.destroy();
  pending.forEach(resolve=>resolve({ok:true,json:async()=>state}));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(sources.length,0);assert.equal(render,null);
});
