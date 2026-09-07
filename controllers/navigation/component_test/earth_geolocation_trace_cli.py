# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Observe Earth geolocation calls without activating its controls."""
from __future__ import annotations

import argparse
import json
import time

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient

_PREFIX = '[earth-trace]'
_INSTALL = r'''(() => {
 const geo = navigator.geolocation;
 if (!geo) return {error: 'Geolocation unavailable'};
 if (window.__orcEarthGeoTrace) return {installed: true, existing: true};
 const state = {events: [], next: 1, active: new Map()};
 const record = (type, detail = {}) => {
  state.events.push({time: new Date().toISOString(), type, ...detail});
  if (state.events.length > 500) state.events.shift();
 };
 const original = {
  watchPosition: geo.watchPosition,
  clearWatch: geo.clearWatch,
  getCurrentPosition: geo.getCurrentPosition
 };
 const wrap = (success, error, method) => ({
  success: p => {record(method + '.success', {latitude: p.coords.latitude, longitude: p.coords.longitude}); if (typeof success === 'function') success(p);},
  error: e => {record(method + '.error', {code: e.code, message: e.message}); if (typeof error === 'function') error(e);}
 });
 Object.defineProperty(geo, 'watchPosition', {configurable: true, value: function(success, error, options) {
  record('watchPosition', {options});
  const cb = wrap(success, error, 'watchPosition');
  const id = original.watchPosition.call(geo, cb.success, cb.error, options);
  state.active.set(id, true);
  return id;
 }});
 Object.defineProperty(geo, 'clearWatch', {configurable: true, value: function(id) {
  record('clearWatch', {id}); state.active.delete(id);
  return original.clearWatch.call(geo, id);
 }});
 Object.defineProperty(geo, 'getCurrentPosition', {configurable: true, value: function(success, error, options) {
  record('getCurrentPosition', {options});
  const cb = wrap(success, error, 'getCurrentPosition');
  return original.getCurrentPosition.call(geo, cb.success, cb.error, options);
 }});
 state.snapshot = () => ({activeWatchers: state.active.size, events: state.events.slice()});
 state.restore = () => {
  for (const [name, fn] of Object.entries(original)) Object.defineProperty(geo, name, {configurable: true, value: fn});
  delete window.__orcEarthGeoTrace;
 };
 window.__orcEarthGeoTrace = state;
 record('trace.installed', {existingBridge: !!window.__orcEarthGeoBridge?.installed});
 return {installed: true, existingBridge: !!window.__orcEarthGeoBridge?.installed};
})()'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=30.0)
    args = parser.parse_args()
    client = ChromiumDevToolsClient(port=9223)
    try:
        result = client.evaluate_earth(_INSTALL)
        print(_PREFIX, json.dumps(result, sort_keys=True), flush=True)
        if not isinstance(result, dict) or not result.get('installed'):
            return 2
        print(_PREFIX, 'Click the actual Earth location control once. No automatic clicks or synthetic fixes.', flush=True)
        deadline = time.monotonic() + args.seconds
        seen = 0
        while time.monotonic() < deadline:
            snapshot = client.evaluate_earth('window.__orcEarthGeoTrace?.snapshot() ?? null')
            if snapshot is None:
                print(_PREFIX, 'Trace lost, possibly due to page navigation.', flush=True)
                return 3
            events = snapshot['events']
            for event in events[seen:]:
                print(_PREFIX, json.dumps(event, sort_keys=True), flush=True)
            seen = len(events)
            time.sleep(0.5)
        print(_PREFIX, 'Observation complete. Active watchers:', snapshot['activeWatchers'], flush=True)
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(_PREFIX, 'FAIL:', exc, flush=True)
        return 2
    except KeyboardInterrupt:
        print('\n' + _PREFIX, 'Stopped.', flush=True)
        return 0
    finally:
        try:
            client.evaluate_earth('window.__orcEarthGeoTrace?.restore(); true')
        except (OSError, RuntimeError, ValueError):
            pass


if __name__ == '__main__':
    raise SystemExit(main())
