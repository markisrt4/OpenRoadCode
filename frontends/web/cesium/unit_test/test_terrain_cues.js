'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../terrain_cues.js'),'utf8'),context);

test('terrain cues restore the prior globe presentation when disabled',()=>{
  let renders=0;
  const original={name:'original'};
  const contour={name:'contour'};
  const globe={enableLighting:false,material:original};
  const viewer={scene:{globe,requestRender(){renders++;}}};
  const C={Material:{fromType(type,options){assert.equal(type,'ElevationContour');assert.equal(options.spacing,10);return contour;}},
    Color:{fromCssColorString(){return {withAlpha(value){assert.equal(value,.58);return 'color';}}}}};
  const cues=context.window.ORCTerrainCues(viewer,C);
  cues.setEnabled(true);
  assert.equal(globe.enableLighting,true);
  assert.equal(globe.material,contour);
  cues.setEnabled(false);
  assert.equal(globe.enableLighting,false);
  assert.equal(globe.material,original);
  assert.equal(renders,2);
});
