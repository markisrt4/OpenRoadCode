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
  const C={Material:class {
    constructor(options){
      const fabric=options.fabric;
      assert.equal(fabric.materials.contours.type,'ElevationContour');
      assert.equal(fabric.uniforms.waterReference,'/data/world-reference.png');
      assert.match(fabric.components.alpha,/providerWaterMask\*materialInput.waterMask/);
      assert.equal(fabric.uniforms.providerWaterMask,0);
      assert.match(fabric.components.alpha,/czm_ellipsoidTextureCoordinates/);
      assert.match(fabric.components.alpha,/czm_inverseView/);
      spacings.push(fabric.materials.contours.uniforms.spacing);
      Object.assign(this,contour);
      let spacing=fabric.materials.contours.uniforms.spacing;
      const uniforms={};
      Object.defineProperty(uniforms,'spacing',{get:()=>spacing,set:value=>{spacing=value;spacings.push(value);}});
      this.materials={contours:{uniforms}};
      Object.defineProperty(this,'spacing',{get:()=>spacing});
    }
  },Color:{fromCssColorString(value){assert.equal(value,'#69a7bd');return {withAlpha(value){assert.equal(value,.46);return 'color';}}}}};
  const cues=context.window.ORCTerrainCues(viewer,C);
  cues.setEnabled(true);
  assert.equal(globe.enableLighting,true);
  assert.equal(globe.material.spacing,10);
  cues.setScale(3);
  assert.equal(globe.material.spacing,30);
  cues.setScale(4);
  assert.equal(globe.material.spacing,40);
  assert.throws(()=>cues.setScale(5),/scale/);
  cues.setEnabled(false);
  assert.equal(globe.enableLighting,false);
  assert.equal(globe.material,original);
  assert.deepEqual(spacings,[10,30,40]);
  assert.equal(renders,4);
});
