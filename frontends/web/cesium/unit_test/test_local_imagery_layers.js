'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
let now=0;
const context={window:{},Date:{now:()=>now}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_imagery_layers.js'),'utf8'),context);
test('regional background survives leaving detail and late loads cannot attach after close',async()=>{
  const layers=[];
  let visible=true,render,resolveDetail=null;
  const C={Color:{TRANSPARENT:{}},GridImageryProvider:class {},
    Rectangle:{fromRadians:()=>({}),intersection:()=>visible?{}:undefined},
    SingleTileImageryProvider:{fromUrl:async url=>{
      if (url==='detail' && resolveDetail!==null) return new Promise(resolve=>{resolveDetail=resolve;});
      return {url};
    }}};
  const viewer={isDestroyed:()=>false,camera:{computeViewRectangle:()=>({})},
    scene:{globe:{ellipsoid:{}},requestRender(){},postRender:{addEventListener(callback){render=callback;return ()=>{render=null;};}}},
    imageryLayers:{get length(){return layers.length;},addImageryProvider(provider,index){
      const layer={provider};layers.splice(index,0,layer);return layer;
    },remove(layer){layers.splice(layers.indexOf(layer),1);}}};
  const snapshot=['overview','detail'].map(url=>({url,west_rad:0,east_rad:1,south_rad:0,north_rad:1,attribution:'source'}));
  const stack=await context.window.ORCLocalImageryLayers(viewer,snapshot,C);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(layers[1].provider.url,'overview');
  assert.equal(layers[2].provider.url,'detail');
  visible=false;now+=600;render();
  assert.equal(layers.length,2);
  assert.equal(layers[1].provider.url,'overview');
  visible=true;resolveDetail=true;now+=600;render();
  await Promise.resolve();
  stack.destroy();
  resolveDetail({url:'detail'});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(layers.length,0);
  assert.equal(render,null);
});
