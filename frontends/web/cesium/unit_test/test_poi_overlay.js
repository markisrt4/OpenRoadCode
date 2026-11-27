'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');

test('dynamic POI snapshots replace markers at terrain-relative positions',async()=>{
  let renders=0;const values=[];const color={};
  const source={entities:{removeAll(){values.length=0;},add(value){values.push(value);return value;}}};
  const C={CustomDataSource:class {constructor(){return source;}},
    Cartesian3:{fromRadians:(...args)=>args},Cartesian2:class {},DistanceDisplayCondition:class {},
    Color:{BLACK:color,WHITE:color,fromCssColorString:()=>color},LabelStyle:{FILL_AND_OUTLINE:1}};
  color.withAlpha=()=>color;
  const viewer={dataSources:{add:async()=>source,remove(){}},scene:{requestRender(){renders++;}}};
  const context={window:{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../poi_overlay.js'),'utf8'),context);
  const overlay=context.window.ORCPoiOverlay(viewer,C,()=>7);
  assert.equal(overlay.update({markers:[{id:'one',longitude_rad:-1.4,latitude_rad:.7,label:'Cafe'}]}),true);
  assert.equal(values.length,2);assert.equal(values[0].label.text,'◆');
  assert.deepEqual(values[0].position,[-1.4,.7,19]);
  assert.equal(values[1].show,false);
  assert.equal(overlay.focus('poi-one'),true);assert.equal(values[1].show,true);
  assert.equal(overlay.select('poi-one'),true);
  assert.equal(overlay.consumeSelection(),'one');
  assert.equal(overlay.consumeSelection(),null);
  assert.equal(overlay.select('route-line'),false);
  overlay.update({markers:[]});assert.equal(values.length,0);assert.equal(renders,3);
});
