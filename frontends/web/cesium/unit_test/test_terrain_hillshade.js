'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
let renderCallback;
const document={createElement(){
  const context={createImageData(width,height){return {data:new Uint8ClampedArray(width*height*4)};},
    putImageData(){}};
  return {getContext:()=>context,toDataURL:()=>"data:image/png;base64,test"};
}};
const context={window:{},document,Date,Set,Math,Uint8ClampedArray};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../terrain_hillshade.js'),'utf8'),context);

test('hillshade bounds visible overlays and removes them when disabled',async()=>{
  const layers=[];
  const tile=index=>({west_rad:index,south_rad:0,east_rad:index+1,north_rad:1,width:2,height:2,
    heights_m:[100,101,102,103],detail_level:index===6?2:1,attribution:'USGS'});
  const C={Rectangle:{fromRadians:(west,south,east,north)=>({west,south,east,north}),intersection:()=>({})},
    SingleTileImageryProvider:{fromUrl:async url=>({url})}};
  const viewer={isDestroyed:()=>false,camera:{computeViewRectangle:()=>({})},
    scene:{globe:{ellipsoid:{}},requestRender(){},postRender:{addEventListener(callback){renderCallback=callback;return()=>{renderCallback=null;};}}},
    imageryLayers:{get length(){return layers.length;},addImageryProvider(provider){const layer={provider};layers.push(layer);return layer;},
      remove(layer){layers.splice(layers.indexOf(layer),1);},raiseToTop(){}}};
  const shade=context.window.ORCTerrainHillshade(viewer,{tiles:Array.from({length:7},(_,i)=>tile(i)),attribution:'USGS'},C);
  shade.setEnabled(true);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(layers.length,6);
  renderCallback();
  shade.setEnabled(false);
  assert.equal(layers.length,0);
  shade.destroy();
  assert.equal(renderCallback,null);
});
