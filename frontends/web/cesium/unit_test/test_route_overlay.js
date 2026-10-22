'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');

test('route snapshots draw clamped lines and clear old entities',()=>{
  let renders=0;const values=[];const color={withAlpha:()=>color};
  const source={entities:{removeAll(){values.length=0;},add(value){values.push(value);return value;}}};
  const C={CustomDataSource:class {constructor(){return source;}},
    Cartesian3:{fromRadians:(...args)=>args},Cartesian2:class {},DistanceDisplayCondition:class {},
    Color:{BLACK:color,WHITE:color,fromCssColorString:()=>color},LabelStyle:{FILL_AND_OUTLINE:1}};
  const viewer={dataSources:{add:()=>source,remove(){}},scene:{requestRender(){renders++;}}};
  const context={window:{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../route_overlay.js'),'utf8'),context);
  const overlay=context.window.ORCRouteOverlay(viewer,C,()=>7);
  const point=(latitude_rad,longitude_rad)=>({latitude_rad,longitude_rad});
  assert.equal(overlay.update({points:[point(.7,-1.4),point(.71,-1.39)],destination:point(.71,-1.39)}),true);
  assert.equal(values.length,3);
  assert.equal(values[0].polyline.clampToGround,true);
  assert.deepEqual(values[1].polyline.positions[0],[-1.4,.7,10]);
  overlay.update({points:[]});
  assert.equal(values.length,0);
  assert.equal(renders,2);
});
