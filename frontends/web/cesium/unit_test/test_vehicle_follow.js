'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../vehicle_follow.js'),'utf8'),context);
test('vehicle marker follows live fixes, retains view range and hides on fix loss',()=>{
  let marker,anchor,pose,renders=0;
  const C={Color:{YELLOW:{},BLACK:{}},Cartesian2:class {},
    Cartesian3:{fromRadians:(longitude,latitude,height)=>({longitude,latitude,height}),distance:()=>800},
    HeadingPitchRange:class {constructor(heading,pitch,range){Object.assign(this,{heading,pitch,range});}},
    Matrix4:{IDENTITY:{}}};
  const camera={heading:.6,pitch:-.7,positionWC:{},getPickRay:()=>({}),
    lookAt(target,orientation){anchor=target;pose=orientation;},lookAtTransform(){}};
  const viewer={camera,entities:{add(entity){marker=entity;return entity;}},scene:{canvas:{clientWidth:600,clientHeight:400},
    globe:{pick:()=>({})},requestRender(){renders++;}}};
  const update=context.window.ORCVehicleFollow(viewer,{distance_m:1500},C,()=>23);
  update({longitude_rad:-1.4,latitude_rad:.7},true);
  assert.equal(marker.show,true);
  assert.equal(marker.position.height,25);
  assert.equal(anchor.height,23); // Camera target uses ground, avoiding cumulative altitude drift.
  assert.equal(pose.range,800);
  assert.equal(pose.heading,.6);
  assert.equal(pose.pitch,-.7);
  anchor=null;
  update({longitude_rad:-1.41,latitude_rad:.71},false);
  assert.equal(marker.position.longitude,-1.41);
  assert.equal(anchor,null);
  update(null,true);
  assert.equal(marker.show,false);
  assert.equal(anchor,null);
  assert.equal(renders,3);
});
