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
  const spacings=[];
  const C={Material:{fromType(type,options){assert.equal(type,'ElevationContour');spacings.push(options.spacing);return {...contour,spacing:options.spacing};}},
    Color:{fromCssColorString(){return {withAlpha(value){assert.equal(value,.58);return 'color';}}}}};
  const cues=context.window.ORCTerrainCues(viewer,C);
  cues.setEnabled(true);
  assert.equal(globe.enableLighting,true);
  assert.equal(globe.material.spacing,10);
  cues.setScale(3);
  assert.equal(globe.material.spacing,30);
  cues.setEnabled(false);
  assert.equal(globe.enableLighting,false);
  assert.equal(globe.material,original);
  assert.deepEqual(spacings,[10,30]);
  assert.equal(renders,3);
});
