'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
function context(){
  const scope={window:{}}; // Deliberately no document/canvas or GeoJSON fetch.
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../reference_globe_layer.js'),'utf8'),scope);
  return scope;
}
test('reference does not attach after viewer closes during image load',async()=>{
  let resolve,attached=0,destroyed=false;
  const C={Rectangle:{fromRadians:(...values)=>values},SingleTileImageryProvider:{
    fromUrl:()=>new Promise(done=>{resolve=done;})
  }};
  const viewer={isDestroyed:()=>destroyed,imageryLayers:{addImageryProvider(){attached++;}}};
  const pending=context().window.ORCReferenceGlobeLayer(viewer,C);
  destroyed=true;resolve({});
  assert.equal(await pending,null);
  assert.equal(attached,0);
});
test('offline opaque reference loads once without canvas and stays at bottom',async()=>{
  let requested=0,attached=0;
  const C={Rectangle:{fromRadians:(...values)=>values},SingleTileImageryProvider:{
    fromUrl:async(url,options)=>{
      requested++;
      assert.equal(url,'/data/world-reference.png');
      assert.deepEqual(Array.from(options.rectangle),[-Math.PI,-Math.PI/2,Math.PI,Math.PI/2]);
      return {};
    }
  }};
  const layer={};
  const viewer={isDestroyed:()=>false,imageryLayers:{addImageryProvider(provider,index){
    attached++;assert.equal(index,0);assert.equal(provider.orcLayerRole,'reference-globe');return layer;
  }}};
  const scope=context();
  assert.equal(await scope.window.ORCReferenceGlobeLayer(viewer,C),layer);
  assert.equal(await scope.window.ORCReferenceGlobeLayer(viewer,C),layer);
  assert.equal(requested,1);assert.equal(attached,1);
});
