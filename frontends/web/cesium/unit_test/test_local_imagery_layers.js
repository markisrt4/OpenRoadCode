'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
let now=0;
const context={window:{},Date:{now:()=>now},
  fetch:async()=>({ok:true,json:async()=>({features:[]})}),
  document:{createElement:()=>({width:0,height:0,getContext:()=>({fillRect(){}}),
    toDataURL:()=> 'data:image/png;base64,reference'})}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../reference_globe_layer.js'),'utf8'),context);
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_imagery_layers.js'),'utf8'),context);
test('regional background survives leaving detail and late loads cannot attach after close',async()=>{
  const layers=[];
  let visible=true,render,resolveDetail=null;
  const C={Rectangle:{fromRadians:()=>({}),intersection:()=>visible?{}:undefined},
    SingleTileImageryProvider:{fromUrl:async url=>{
      if(url.startsWith('data:image/png;base64,'))return {url};
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
  assert.equal(layers[0].provider.url.startsWith('data:image/png;base64,'),true);
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


test('large installed catalog keeps six resident images and loads detail after panning',async()=>{
  const layers=[];
  let render,western=true,peak=0;
  const C={Rectangle:{fromRadians:west=>({west}),
    intersection:(_view,rectangle)=>western || rectangle.west===0 ? {} : undefined},
    SingleTileImageryProvider:{fromUrl:async url=>({url})}};
  const viewer={isDestroyed:()=>false,camera:{computeViewRectangle:()=>({})},
    scene:{globe:{ellipsoid:{}},requestRender(){},postRender:{addEventListener(callback){render=callback;return ()=>{};}}},
    imageryLayers:{get length(){return layers.length;},addImageryProvider(provider,index){
      const layer={provider};layers.splice(index,0,layer);peak=Math.max(peak,layers.length);return layer;
    },remove(layer){layers.splice(layers.indexOf(layer),1);}}};
  const snapshot=Array.from({length:9},(_,index)=>({url:`pack-${index}`,west_rad:index,
    east_rad:index+1,south_rad:0,north_rad:1,attribution:'source'}));
  const stack=await context.window.ORCLocalImageryLayers(viewer,snapshot,C);
  await new Promise(done=>setImmediate(done));
  assert.deepEqual(layers.slice(1).map(layer=>layer.provider.url),
    ['pack-0','pack-4','pack-5','pack-6','pack-7','pack-8']);
  western=false;now+=600;render();
  assert.equal(layers.length,2);
  western=true;now+=600;render();
  await new Promise(done=>setImmediate(done));
  assert.equal(layers.length,7);
  assert.equal(peak,7); // Six imagery textures plus the reference globe.
  stack.destroy();
  assert.equal(layers.length,0);
});
