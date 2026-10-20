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
  GeographicTilingScheme:class {
    tileXYToRectangle() { return {west:0,south:0,east:1,north:1}; }
  },
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

test('relief scale replaces cached meshes, keeps source elevations and flattens overlays when hidden', () => {
  const terrain = context.window.ORCLocalTerrain(data,C);
  const viewer = {scene:{requestRender(){}}};
  const original = terrain.provider;
  terrain.setScale(viewer,3);
  assert.notEqual(viewer.terrainProvider,original);
  assert.ok(Math.abs(terrain.heightAt(.5,2/3)-15)<1e-10);
  assert.ok(Math.abs(terrain.heightAt(.5,1/3)+15)<1e-10);
  assert.equal(data.heights_m[0],30);
  assert.equal(terrain.heightAt(0,.8),0);
  terrain.setVisible(viewer,false);
  assert.equal(terrain.heightAt(.5,2/3),0);
  terrain.setVisible(viewer,true);
  terrain.setScale(viewer,1);
  assert.ok(Math.abs(terrain.heightAt(.5,2/3)-5)<1e-10);
  assert.throws(()=>terrain.setScale(viewer,4),/Terrain scale/);
});

test('mosaic tiles retain relief at their shared edge', () => {
  const west={...data,west_rad:0,east_rad:1,heights_m:Array(16).fill(20),reference_height_m:10};
  const east={...data,west_rad:1,east_rad:2,heights_m:Array(16).fill(20),reference_height_m:10};
  const mosaic=context.window.ORCLocalTerrain({tiles:[west,east],attribution:'USGS'},C);
  assert.equal(mosaic.heightAt(1,.5),10);
  assert.equal(mosaic.heightAt(1.5,.5),10);
});

test('LOD terrain uses camera-appropriate samples and stops at its declared limit', async () => {
  const overview={...data,heights_m:Array(16).fill(20),reference_height_m:10,
    detail_level:0,minimum_zoom:0};
  const focus={...data,west_rad:.25,east_rad:.75,south_rad:.25,north_rad:.75,
    heights_m:Array(16).fill(40),reference_height_m:10,detail_level:2,minimum_zoom:12};
  const lod=context.window.ORCLocalTerrain({tiles:[overview,focus],attribution:'USGS',maximum_zoom:16},C);
  const coarse=await lod.provider.options.callback(0,0,8);
  const detailed=await lod.provider.options.callback(0,0,12);
  assert.equal(coarse[16*33+16],10);
  assert.equal(detailed[16*33+16],30);
  assert.equal(lod.heightAt(.5,.5),30);
  assert.ok(lod.provider.getLevelMaximumGeometricError(15)>0);
  assert.equal(lod.provider.getLevelMaximumGeometricError(16),0);
});
