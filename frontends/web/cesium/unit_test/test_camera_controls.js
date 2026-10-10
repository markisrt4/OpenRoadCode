'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../camera_controls.js'),'utf8'),context);
test('pitch orbits the panned view centre without losing heading or viewing distance, and stays above ground',()=>{
  let target={x:1};
  let renders=0,transforms=0;
  const camera={getPickRay:()=>({}),pickEllipsoid:()=>undefined,pitch:-Math.PI/4,heading:.6,positionWC:{x:1201},
    lookAt(point,pose){ assert.equal(point,target); assert.equal(pose.heading,.6);
      assert.equal(pose.range,1201-target.x); this.pitch=pose.pitch; },
    lookAtTransform(){transforms++;}};
  const C={Cartesian2:class {constructor(x,y){Object.assign(this,{x,y});}},Cartesian3:{distance:(a,b)=>a.x-b.x},Matrix4:{IDENTITY:{}},
    HeadingPitchRange:class {constructor(heading,pitch,range){Object.assign(this,{heading,pitch,range});}}};
  const state={pitch_step_rad:Math.PI/18,maximum_tilt_rad:80*Math.PI/180};
  const controls=context.window.ORCCameraControls({camera,scene:{canvas:{clientWidth:800,clientHeight:600},globe:{pick:()=>target},requestRender(){renders++;}}},state,C);
  assert.ok(Math.abs(controls.pitch(1)-55*Math.PI/180)<1e-10);
  target={x:201}; // Mouse pan has moved the centre away from the original destination.
  for(let i=0;i<20;i++) controls.pitch(1);
  assert.ok(Math.abs(camera.pitch-(state.maximum_tilt_rad-Math.PI/2))<1e-10);
  for(let i=0;i<20;i++) controls.pitch(-1);
  assert.equal(camera.pitch,-Math.PI/2);
  assert.equal(renders,41); assert.equal(transforms,41);
});

test('sky-centred tilt changes orientation in place without recentering',()=>{
  let orientation;
  const camera={pitch:-.3,heading:.5,roll:0,getPickRay:()=>({}),pickEllipsoid:()=>undefined,
    setView(options){orientation=options.orientation;},
    lookAt(){throw Error('Must not recenter');}};
  const C={Cartesian2:class {}};
  const viewer={camera,scene:{canvas:{clientWidth:800,clientHeight:600},globe:{pick:()=>undefined},requestRender(){}}};
  context.window.ORCCameraControls(viewer,{pitch_step_rad:.1,maximum_tilt_rad:1.4},C).pitch(-1);
  assert.equal(orientation.heading,.5);
  assert.ok(Math.abs(orientation.pitch+.4)<1e-10);
});

test('pan follows view heading, scales with zoom and retains orientation and range',()=>{
  let next, pose;
  let range=1200;
  const camera={heading:0,pitch:-.6,positionWC:{},getPickRay:()=>({}),pickEllipsoid:()=>undefined,
    lookAt(point,orientation){next=point;pose=orientation;},lookAtTransform(){}};
  const C={Cartesian2:class {},Cartographic:{fromCartesian:p=>p},
    Cartesian3:{distance:()=>range,fromRadians:(longitude,latitude,height)=>({longitude,latitude,height})},
    HeadingPitchRange:class {constructor(heading,pitch,range){Object.assign(this,{heading,pitch,range});}},Matrix4:{IDENTITY:{}}};
  const scene={canvas:{clientWidth:800,clientHeight:600},globe:{pick:()=>({longitude:0,latitude:0}),ellipsoid:{maximumRadius:6378137}},requestRender(){}};
  const controls=context.window.ORCCameraControls({camera,scene},{pan_step_fraction:.15},C,()=>30);
  controls.pan(0,1);
  assert.ok(next.latitude>0); assert.equal(next.longitude,0);
  assert.equal(next.height,30); assert.equal(pose.pitch,-.6); assert.equal(pose.range,1200);
  const initialLatitude=next.latitude;
  range=600;
  controls.pan(0,1);
  assert.ok(Math.abs(next.latitude-initialLatitude/2)<1e-10);
  camera.heading=Math.PI/2;
  controls.pan(0,1);
  assert.ok(next.longitude>0); assert.ok(Math.abs(next.latitude)<1e-10);
  controls.pan(1,0);
  assert.ok(next.latitude<0);
  scene.globe.pick=()=>undefined;
  assert.equal(controls.pan(1,0),false);
});
