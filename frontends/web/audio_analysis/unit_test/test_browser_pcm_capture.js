// SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
// SPDX-License-Identifier: MIT
const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function deferred() {
  let resolve;
  const promise = new Promise(r => {resolve = r;});
  return {promise, resolve};
}
function load(overrides = {}) {
  const context = {window: {}, navigator: {}, console, Int16Array, ...overrides};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../browser_pcm_capture.js'), 'utf8'), context);
  return new context.window.OpenRoadCodeWeb.BrowserPcmCapture();
}
test('late PCM response cannot publish state or clear a new request', async () => {
  const response = deferred();
  let request;
  const capture = load({fetch: (url, options) => {
    request = {url, options};
    return response.promise;
  }});
  let callbacks = 0;
  capture.running = true;
  capture.audioContext = {sampleRate: 48000, close: async () => {}};
  capture.onState = () => callbacks++;
  const sending = capture._send(new Float32Array([0.5, -0.5]));
  assert.equal(request.url, '/api/audio-analysis/session/pcm16');
  assert.equal(request.options.headers['X-Audio-Source'], 'browser');
  await capture.stop();
  capture.running = true;
  capture.inFlight = true;
  response.resolve({ok: true, json: async () => ({running: true})});
  await sending;
  assert.equal(callbacks, 0);
  assert.equal(capture.inFlight, true);
});
test('canceling pending microphone permission releases the late stream', async () => {
  const permission = deferred();
  let stopped = 0;
  const capture = load({navigator: {mediaDevices: {getUserMedia: () => permission.promise}}});
  const starting = capture.start(() => {});
  await capture.stop();
  permission.resolve({getTracks: () => [{stop: () => stopped++}]});
  await assert.rejects(starting, /canceled/);
  assert.equal(stopped, 1);
  assert.equal(capture.audioContext, null);
});
test('closing an old context does not clear replacement resources', async () => {
  const closing = deferred();
  const capture = load();
  capture.audioContext = {close: () => closing.promise};
  const stopping = capture.stop();
  const replacement = {};
  capture.audioContext = replacement;
  closing.resolve();
  await stopping;
  assert.equal(capture.audioContext, replacement);
});
