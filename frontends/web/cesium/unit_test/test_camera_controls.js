'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../camera_controls.js'),'utf8'),context);
test('pitch orbits the destination without losing heading or viewing distance, and stays above ground',()=>{
  const target={x:1};
  let renders=0,transforms=0;
  const camera={pitch:-Math.PI/4,heading:.6,positionWC:{x:1201},
    lookAt(point,pose){ assert.equal(point,target); assert.equal(pose.heading,.6);
      assert.equal(pose.range,1200); this.pitch=pose.pitch; },
    lookAtTransform(){transforms++;}};
  const C={Cartesian3:{distance:(a,b)=>a.x-b.x},Matrix4:{IDENTITY:{}},
    HeadingPitchRange:class {constructor(heading,pitch,range){Object.assign(this,{heading,pitch,range});}}};
  const state={pitch_step_rad:Math.PI/18,maximum_tilt_rad:80*Math.PI/180};
  const controls=context.window.ORCCameraControls({camera,scene:{requestRender(){renders++;}}},target,state,C);
  assert.ok(Math.abs(controls.pitch(1)-55*Math.PI/180)<1e-10);
  for(let i=0;i<20;i++) controls.pitch(1);
  assert.ok(Math.abs(camera.pitch-(state.maximum_tilt_rad-Math.PI/2))<1e-10);
  for(let i=0;i<20;i++) controls.pitch(-1);
  assert.equal(camera.pitch,-Math.PI/2);
  assert.equal(renders,41); assert.equal(transforms,41);
});
