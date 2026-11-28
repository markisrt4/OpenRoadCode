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
  class PolylineDashMaterialProperty {constructor(options){Object.assign(this,options);}}
  const C={CustomDataSource,Cartesian3:{fromRadiansArray:value=>value},
    Color:{fromCssColorString:value=>({value,withAlpha(alpha){return {value,alpha};}})},
    PolylineDashMaterialProperty,
    Credit:class {constructor(value){this.value=value;}}};
  const viewer={dataSources:{add(){},remove(source,destroy){removed={source,destroy};}},
    cesiumWidget:{creditDisplay:{addStaticCredit(value){credit=value;}}},
    scene:{requestRender(){renders++;}}};
  const path=[[0,0],[1,0],[1,1]];
  const overlay=context.window.ORCBoundaryOverlay(viewer,{attribution:'Census',regions:[
    {name:'Countries',kind:'country',emphasized:false,paths_rad:[path]},
    {name:'Disputed',kind:'disputed',emphasized:false,paths_rad:[path]},
    {name:'State boundaries',kind:'state',emphasized:false,paths_rad:[path]},
    {name:'Michigan',kind:'state',emphasized:true,paths_rad:[path]},
  ]},C);
  assert.equal(entities.length,4);
  assert.equal(entities[0].polyline.width,1.8);
  assert.equal(entities[0].polyline.material.dashLength,18);
  assert.equal(entities[0].polyline.material.dashPattern,0x0fff);
  assert.equal(entities[1].polyline.material.dashPattern,0x00ff);
  assert.equal(entities[2].polyline.material.color.alpha,.45);
  assert.equal(entities[2].polyline.material.dashPattern,0x000f);
  assert.equal(entities[3].polyline.width,2.5);
  assert.equal(entities[3].polyline.material.color.value,'#59d8ff');
  assert.equal(credit.value,'Census');
  assert.equal(renders,1);
  overlay.destroy();
  assert.deepEqual(removed,{source:overlay.source,destroy:true});
});
