'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const test=require('node:test');
test('layer controls report availability, use shared handlers, and hide late imagery without rendering callbacks',()=>{
  let added,removed=false,closed=false;
  const hillshade={show:true,imageryProvider:{orcLayerRole:'terrain-cues'}};
  const layers=[{show:true},hillshade];
  const viewer={isDestroyed:()=>closed,scene:{requestRender(){}},imageryLayers:{
    get length(){return layers.length;},get:index=>layers[index],
    layerAdded:{addEventListener(callback){added=callback;return()=>{removed=true;};}}}};
  const buttons={};
  for(const action of ['buildings','roads','places','terrain','terrain-scale','terrain-cues','references']) {
    const button={disabled:action==='buildings',textContent:action==='terrain-scale'?'Height 2×':action,
      enabled:false,getAttribute(){return String(this.enabled);},onclick(){this.enabled=!this.enabled;}};
    buttons[action]=button;
  }
  const context={window:{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../map_layer_controls.js'),'utf8'),context);
  const controls=context.window.ORCMapLayers(viewer,{imagery_layers:[{}]}, {getElementById:id=>buttons[id]});
  assert.equal(controls.state().find(item=>item.action==='buildings').available,false);
  assert.equal(controls.request('buildings'),false);
  assert.equal(controls.request('places'),true);
  assert.equal(controls.state().find(item=>item.action==='places').enabled,true);
  assert.equal(controls.state().find(item=>item.action==='terrain-scale').label,'Height 2×');
  assert.equal(controls.request('imagery'),true);
  assert.equal(layers[0].show,false);
  assert.equal(hillshade.show,true,'terrain cues remain independently controlled');
  const lateCues={show:true,imageryProvider:{orcLayerRole:'terrain-cues'}};added(lateCues);assert.equal(lateCues.show,true);
  const late={show:true};added(late);assert.equal(late.show,false);
  assert.equal(controls.request('anything-else'),false);
  controls.destroy();assert.equal(removed,true);
  assert.equal(controls.request('roads'),false);
  closed=true;
});
