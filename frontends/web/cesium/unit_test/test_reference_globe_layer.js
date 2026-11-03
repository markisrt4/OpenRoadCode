'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../reference_globe_layer.js'),'utf8'),context);

test('blue base does not attach after viewer closes during image load',async()=>{
  let resolve,attached=0,destroyed=false;
  const C={Rectangle:{fromRadians:(...values)=>values},SingleTileImageryProvider:{
    fromUrl:()=>new Promise(done=>{resolve=done;})
  }};
  const viewer={isDestroyed:()=>destroyed,imageryLayers:{addImageryProvider(){attached++;}}};
  const pending=context.window.ORCReferenceGlobeLayer(viewer,C);
  destroyed=true;
  resolve({url:'base'});
  assert.equal(await pending,null);
  assert.equal(attached,0);
});
