'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const test = require('node:test');
const context = {window:{}, Float32Array};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../local_terrain.js'),'utf8'),context);
const C = {
  EllipsoidTerrainProvider:class {},
  GeographicTilingScheme:class {},
  CustomHeightmapTerrainProvider:class {
    constructor(options) { this.options=options; }
    getLevelMaximumGeometricError(level) { return 10000/(2**level); }
  }
};
const data = {west_rad:0,south_rad:0,east_rad:1,north_rad:1,width:4,height:4,
  heights_m:[30,30,30,30,20,20,20,20,10,10,10,10,0,0,0,0],reference_height_m:15,attribution:'Test'};
const terrain = context.window.ORCLocalTerrain(data,C);
test('north-first source rows interpolate correctly without changing original elevations', () => {
  assert.ok(Math.abs(terrain.heightAt(.5,2/3)-5)<1e-10);
  assert.ok(Math.abs(terrain.heightAt(.5,1/3)+5)<1e-10);
  assert.equal(terrain.heightAt(.5,.5),0);
  assert.equal(data.heights_m[0],30);
});
test('outside coverage and its outer edge return flat relief', () => {
  assert.equal(terrain.heightAt(-.1,.5),0);
  assert.equal(terrain.heightAt(.5,1.1),0);
  assert.equal(terrain.heightAt(0,.8),0);
});
test('renderer does not refine beyond the prototype terrain detail limit', () => {
  assert.ok(terrain.provider.getLevelMaximumGeometricError(12)>0);
  assert.equal(terrain.provider.getLevelMaximumGeometricError(13),0);
});

test('flat comparison keeps the camera and restores the sampled provider', () => {
  let renders=0;
  const camera={heading:1,pitch:-.5};
  const viewer={camera,scene:{requestRender:()=>renders++}};
  terrain.setVisible(viewer,false);
  assert.ok(viewer.terrainProvider instanceof C.EllipsoidTerrainProvider);
  terrain.setVisible(viewer,true);
  assert.equal(viewer.terrainProvider,terrain.provider);
  assert.deepEqual(viewer.camera,{heading:1,pitch:-.5});
  assert.equal(renders,2);
});
