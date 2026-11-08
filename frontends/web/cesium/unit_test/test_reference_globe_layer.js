'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const draw=[];
const canvasContext={fillStyle:null,fillRect(...args){draw.push(['fill',this.fillStyle,...args]);},
  beginPath(){},moveTo(){},lineTo(){},closePath(){},fill(rule){draw.push(['land',this.fillStyle,rule]);}};
const context={window:{},fetch:async()=>({ok:true,json:async()=>({features:[{geometry:{type:'Polygon',
  coordinates:[[[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]]]}}]})}),document:{createElement:()=>({
  width:0,height:0,getContext:()=>canvasContext,toDataURL:()=> 'data:image/png;base64,reference'})}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../reference_globe_layer.js'),'utf8'),context);

test('blue base does not attach after viewer closes during image load',async()=>{
  let resolve,attached=0,destroyed=false;
  const C={Rectangle:{fromRadians:(...values)=>values},SingleTileImageryProvider:{
    fromUrl:()=>new Promise(done=>{resolve=done;})
  }};
  const viewer={isDestroyed:()=>destroyed,imageryLayers:{addImageryProvider(){attached++;}}};
  const pending=context.window.ORCReferenceGlobeLayer(viewer,C);
  // The offline land/lake reads complete before the image-provider load starts.
  await new Promise(done=>setImmediate(done));
  assert.equal(typeof resolve,'function');
  destroyed=true;
  resolve({url:'base'});
  assert.equal(await pending,null);
  assert.equal(attached,0);
  assert.deepEqual(draw[0],['fill','#174963',0,0,2048,1024]);
  assert.deepEqual(draw.at(-2),['land','#456f4e','evenodd']);
  assert.deepEqual(draw.at(-1),['land','#174963','evenodd']);
});
