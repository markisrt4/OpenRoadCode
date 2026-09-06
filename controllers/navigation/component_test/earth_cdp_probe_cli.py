# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe the live Google Earth page through Chromium DevTools."""

from __future__ import annotations

import argparse
import json

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_cdp_camera_controller import EarthCdpCameraController


def _command_name(call: dict) -> str:
    args=call.get("args")
    if not isinstance(args,list) or not args or not isinstance(args[0],dict): return ""
    return str(args[0].get("preview") or "")


def _print_trace(controller: EarthCdpCameraController, *, suppress_input_events: bool=False) -> None:
    calls=controller.read_command_trace()
    if suppress_input_events: calls=tuple(c for c in calls if _command_name(c)!="earth.InputEvent")
    print(f"captured calls: {len(calls)}")
    for index,call in enumerate(calls,1):
        print(f"  call {index}:")
        args=call.get("args")
        if not isinstance(args,list): continue
        for arg_index,arg in enumerate(args,1):
            if not isinstance(arg,dict): continue
            print(f"    arg {arg_index}: type={arg.get('type')} constructor={arg.get('constructorName')} length={arg.get('length')} byteLength={arg.get('byteLength')}")
            keys=arg.get("keys"); preview=arg.get("preview")
            if isinstance(keys,list) and keys: print(f"      keys: {', '.join(str(k) for k in keys)}")
            if preview: print(f"      preview: {preview}")


def _probe_geolocation(latitude: float, longitude: float, accuracy_m: float) -> None:
    client=ChromiumDevToolsClient(port=9223); client.set_geolocation_override(latitude,longitude,accuracy_m=accuracy_m)
    observed=client.evaluate_earth("""(() => new Promise(resolve => {if(!navigator.geolocation){resolve({ok:false,error:'navigator.geolocation unavailable'});return;}navigator.geolocation.getCurrentPosition(position=>resolve({ok:true,latitude:position.coords.latitude,longitude:position.coords.longitude,accuracy:position.coords.accuracy}),error=>resolve({ok:false,error:error.message,code:error.code}),{enableHighAccuracy:true,timeout:5000,maximumAge:0});}))()""")
    print(f"CDP geolocation override set: {latitude:.7f}, {longitude:.7f} accuracy={accuracy_m:g}m")
    print(f"Earth page navigator.geolocation reports: {observed}")


def _install_geolocation_trace(client: ChromiumDevToolsClient) -> bool:
    value=client.evaluate_earth(r"""(() => {
      const geo=navigator.geolocation;
      if(!geo) return false;
      if(window.__orcGeoTrace?.installed) { window.__orcGeoTrace.events.length=0; return true; }
      const trace={installed:true,events:[],nextId:1};
      const push=(kind,data={})=>{trace.events.push({time:Date.now(),kind,...data});if(trace.events.length>200)trace.events.shift();};
      const snap=p=>({
        latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy,
        altitude:p.coords.altitude,altitudeAccuracy:p.coords.altitudeAccuracy,
        heading:p.coords.heading,speed:p.coords.speed,timestamp:p.timestamp
      });
      const originalGet=geo.getCurrentPosition.bind(geo);
      const originalWatch=geo.watchPosition.bind(geo);
      const originalClear=geo.clearWatch.bind(geo);
      Object.defineProperty(geo,'getCurrentPosition',{configurable:true,value:function(success,error,options){
        const id=trace.nextId++;push('getCurrentPosition',{id,options:options||null});
        return originalGet(p=>{push('getCurrentPosition.success',{id,position:snap(p)});if(success)success(p);},e=>{push('getCurrentPosition.error',{id,code:e.code,message:e.message});if(error)error(e);},options);
      }});
      Object.defineProperty(geo,'watchPosition',{configurable:true,value:function(success,error,options){
        const id=trace.nextId++;push('watchPosition',{id,options:options||null});
        const browserId=originalWatch(p=>{push('watchPosition.success',{id,browserId,position:snap(p)});if(success)success(p);},e=>{push('watchPosition.error',{id,browserId,code:e.code,message:e.message});if(error)error(e);},options);
        push('watchPosition.registered',{id,browserId});return browserId;
      }});
      Object.defineProperty(geo,'clearWatch',{configurable:true,value:function(browserId){push('clearWatch',{browserId});return originalClear(browserId);}});
      window.__orcGeoTrace=trace;
      return true;
    })()""")
    return value is True


def _read_geolocation_trace(client: ChromiumDevToolsClient) -> dict:
    value=client.evaluate_earth(r"""(async () => {
      let permission='unknown';
      try { permission=(await navigator.permissions.query({name:'geolocation'})).state; } catch(_) {}
      return {
        permission,
        visibility:document.visibilityState,
        hasFocus:document.hasFocus(),
        events:window.__orcGeoTrace?.events || []
      };
    })()""")
    return value if isinstance(value,dict) else {}


def _trace_geolocation() -> None:
    client=ChromiumDevToolsClient(port=9223)
    if not _install_geolocation_trace(client): raise SystemExit("navigator.geolocation is not available")
    before=_read_geolocation_trace(client)
    print(f"geolocation permission: {before.get('permission')}")
    print(f"document visibility: {before.get('visibility')}  focus: {before.get('hasFocus')}")
    print("Geolocation trace installed.")
    print("Click Google Earth's My Location button once. Let it spin for a few seconds, then press Enter here.")
    input()
    result=_read_geolocation_trace(client)
    events=result.get("events") if isinstance(result.get("events"),list) else []
    print(f"geolocation permission: {result.get('permission')}")
    print(f"document visibility: {result.get('visibility')}  focus: {result.get('hasFocus')}")
    print(f"captured geolocation events: {len(events)}")
    for index,event in enumerate(events,1):
        print(f"  {index:02d}: {json.dumps(event,sort_keys=True)}")


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-commands",action="store_true")
    parser.add_argument("--trace-my-location",action="store_true")
    parser.add_argument("--trace-geolocation",action="store_true",help="trace Earth's navigator.geolocation calls and callbacks")
    parser.add_argument("--geolocation",nargs=2,type=float,metavar=("LAT","LON"))
    parser.add_argument("--accuracy-m",type=float,default=5.0)
    parser.add_argument("--clear-geolocation",action="store_true")
    parser.add_argument("--my-location",action="store_true")
    parser.add_argument("--my-location-focused",action="store_true",help="replay only the observed My Location [34,0] then [10,0] sequence")
    parser.add_argument("--my-location-full",action="store_true",help="replay the complete observed non-input My Location sequence")
    args=parser.parse_args()

    controller=EarthCdpCameraController()
    if not controller.available(): raise SystemExit("Google Earth DevTools target is not available")
    if args.clear_geolocation:
        ChromiumDevToolsClient(port=9223).clear_geolocation_override(); print("Google Earth geolocation override cleared."); return
    if args.geolocation is not None:
        _probe_geolocation(*args.geolocation,args.accuracy_m); return
    if args.trace_geolocation:
        _trace_geolocation(); return
    if args.my_location_focused:
        if not controller.trigger_my_location_focused(): raise SystemExit("Earth command bridge is not available")
        print("Replayed My Location [34,0] -> [10,0]."); return
    if args.my_location_full:
        if not controller.trigger_my_location_full_sequence(): raise SystemExit("Earth command bridge is not available")
        print("Replayed complete observed My Location sequence."); return
    if args.my_location:
        if not controller.trigger_my_location(): raise SystemExit("Earth command bridge is not available")
        print("Replayed earlier My Location [18,0] comparison command."); return
    if args.trace_my_location:
        if not controller.install_command_trace(): raise SystemExit("ReceiveViewModelCommand is not available")
        controller.clear_command_trace(); print("Focused My Location trace is active."); print("Click Google Earth's My Location button exactly once, then press Enter here."); input(); _print_trace(controller,suppress_input_events=True); return
    if args.trace_commands:
        if not controller.install_command_trace(): raise SystemExit("ReceiveViewModelCommand is not available")
        controller.clear_command_trace(); print("Tracing ReceiveViewModelCommand. Manipulate Earth, then press Enter."); input(); _print_trace(controller); return

    probe=controller.probe_runtime(); print(f"title: {probe.title}"); print(f"ready: {probe.ready_state}"); print(f"canvas count: {probe.canvas_count}"); print(f"url: {probe.url}")
    inspection=controller.inspect_runtime(); print(f"earthWasmStarted: {inspection.earth_wasm_started}"); print(f"Module present: {inspection.module_present}"); print(f"canvas: {inspection.canvas_width}x{inspection.canvas_height} backing, {inspection.canvas_client_width}x{inspection.canvas_client_height} client")
    print("Module keys:"); [print(f"  {k}") for k in inspection.module_keys]
    print("targeted globals:")
    for item in inspection.globals:
        constructor=f" / {item.constructor_name}" if item.constructor_name else ""; print(f"  {item.name}: {item.value_type}{constructor}")
        if item.keys: print(f"    keys: {', '.join(item.keys)}")
    print("selected Module hooks:")
    for hook in controller.inspect_module_hooks():
        constructor=f" / {hook.constructor_name}" if hook.constructor_name else ""; arity=f", arity={hook.arity}" if hook.arity is not None else ""; embind=f", embind_args={hook.embind_arg_count}" if hook.embind_arg_count is not None else ""
        print(f"  {hook.name}: {hook.value_type}{constructor}{arity}{embind}")
        if hook.keys: print(f"    keys: {', '.join(hook.keys)}")
        if hook.source_preview: print(f"    source: {hook.source_preview}")


if __name__ == "__main__":
    main()
