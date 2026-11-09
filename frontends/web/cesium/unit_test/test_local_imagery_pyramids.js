'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_imagery_pyramids.js'),'utf8'),context);
test('detail uses bounded native zoom tiles and stays above late coarse imagery',()=>{
  const layers=[];
  let listener,unbound=0;
  const C={RequestScheduler:{},UrlTemplateImageryProvider:class {constructor(options){this.options=options;}},
    WebMercatorTilingScheme:class {},Rectangle:{fromRadians:(...values)=>values}};
  const viewer={isDestroyed:()=>false,scene:{globe:{}},imageryLayers:{
    layerAdded:{addEventListener(fn){listener=fn;return ()=>{unbound++;listener=null;};}},
    addImageryProvider(provider){const layer={imageryProvider:provider};layers.push(layer);listener?.(layer);return layer;},
    contains:layer=>layers.includes(layer),raiseToTop(layer){layers.splice(layers.indexOf(layer),1);layers.push(layer);},
    remove(layer){layers.splice(layers.indexOf(layer),1);}}};
  const state={url:'/data/imagery-detail/0/{z}/{x}/{y}',minimum_zoom:10,maximum_zoom:16,tile_size:256,
    west_rad:-1,east_rad:0,south_rad:.1,north_rad:.2,attribution:'NAIP'};
  const controller=context.window.ORCImageryPyramids(viewer,[state],C);
  const detail=layers[0];
  assert.equal(detail.imageryProvider.options.tileWidth,256);
  assert.equal(detail.imageryProvider.options.maximumLevel,16);
  assert.equal(viewer.scene.globe.tileCacheSize,64);
  assert.equal(C.RequestScheduler.maximumRequestsPerServer,6);
  const coarse=viewer.imageryLayers.addImageryProvider({name:'late overview'});
  assert.equal(layers[0],coarse);
  assert.equal(layers.at(-1),detail);
  controller.destroy();controller.destroy();
  assert.deepEqual(layers,[coarse]);assert.equal(unbound,1);
});
