'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../boundary_overlay.js'),'utf8'),context);

test('state boundaries preserve semantic emphasis and clean up with the viewer',()=>{
  const entities=[];let removed=null,credit=null,renders=0;
  class CustomDataSource {constructor(){this.entities={add:value=>(entities.push(value),value)};}}
  const C={CustomDataSource,Cartesian3:{fromRadiansArray:value=>value},
    Color:{fromCssColorString:value=>({value,withAlpha(alpha){return {value,alpha};}})},
    Credit:class {constructor(value){this.value=value;}}};
  const viewer={dataSources:{add(){},remove(source,destroy){removed={source,destroy};}},
    cesiumWidget:{creditDisplay:{addStaticCredit(value){credit=value;}}},
    scene:{requestRender(){renders++;}}};
  const ring=[[0,0],[1,0],[1,1],[0,0]];
  const overlay=context.window.ORCBoundaryOverlay(viewer,{attribution:'Census',regions:[
    {name:'Michigan',emphasized:true,rings_rad:[ring]},
    {name:'Wisconsin',emphasized:false,rings_rad:[ring]},
  ]},C);
  assert.equal(entities.length,2);
  assert.equal(entities[0].polyline.width,3);
  assert.equal(entities[0].polyline.material.value,'#59d8ff');
  assert.equal(entities[1].polyline.width,1.5);
  assert.equal(entities[1].polyline.material.alpha,.5);
  assert.equal(credit.value,'Census');
  assert.equal(renders,1);
  overlay.destroy();
  assert.deepEqual(removed,{source:overlay.source,destroy:true});
});
