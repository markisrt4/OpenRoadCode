# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Preferred Google Earth camera controller using Chromium DevTools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


@dataclass(frozen=True)
class EarthRuntimeProbe:
    title: str
    url: str
    ready_state: str
    canvas_count: int
    custom_element_names: tuple[str, ...]


@dataclass(frozen=True)
class EarthRuntimeObject:
    name: str
    value_type: str
    constructor_name: str
    keys: tuple[str, ...]


@dataclass(frozen=True)
class EarthModuleHook:
    name: str
    value_type: str
    constructor_name: str
    arity: int | None
    embind_arg_count: int | None
    source_preview: str
    keys: tuple[str, ...]


@dataclass(frozen=True)
class EarthRuntimeInspection:
    earth_wasm_started: bool | None
    module_present: bool
    module_keys: tuple[str, ...]
    canvas_width: int | None
    canvas_height: int | None
    canvas_client_width: int | None
    canvas_client_height: int | None
    globals: tuple[EarthRuntimeObject, ...]


class EarthCdpCameraController(EarthCameraControllerIf):
    """Own the stable CDP boundary while Earth camera control is investigated."""

    def __init__(self, client: ChromiumDevToolsClient | None = None) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)

    @property
    def name(self) -> str:
        return "CDP"

    def available(self) -> bool:
        try:
            return self._client.earth_target() is not None
        except (OSError, ValueError):
            return False

    def _send_view_model_commands(self, commands: tuple[tuple[str, tuple[int, ...]], ...]) -> bool:
        """Replay a small sequence of commands observed from Earth's own UI."""
        command_data = json.dumps([[name, list(payload)] for name, payload in commands])
        value = self._client.evaluate_earth(
            """(() => {
                const M = window.Module;
                if (!M || typeof M.ReceiveViewModelCommand !== 'function') return false;
                const commands = """ + command_data + """;
                for (const [name, payload] of commands) {
                    M.ReceiveViewModelCommand(name, new Uint8Array(payload));
                }
                return true;
            })()"""
        )
        return value is True

    def trigger_my_location(self) -> bool:
        """Replay the earlier single My Location command for comparison testing."""
        return self._send_view_model_commands((
            ("earth.mylocation.MyLocationViewModelCommand", (18, 0)),
        ))

    def trigger_my_location_focused(self) -> bool:
        """Replay the two My Location messages observed during a manual recenter."""
        return self._send_view_model_commands((
            ("earth.mylocation.MyLocationViewModelCommand", (34, 0)),
            ("earth.mylocation.MyLocationViewModelCommand", (10, 0)),
        ))

    def trigger_my_location_full_sequence(self) -> bool:
        """Replay the complete non-input sequence observed during a manual recenter."""
        return self._send_view_model_commands((
            ("earth.system.SystemViewModelCommand", (26, 0)),
            ("earth.system.SystemViewModelCommand", (34, 0)),
            ("earth.mylocation.MyLocationViewModelCommand", (34, 0)),
            ("earth.mylocation.MyLocationViewModelCommand", (10, 0)),
            ("earth.mylocation.MyLocationViewModelCommand", (10, 0)),
        ))

    def probe_runtime(self) -> EarthRuntimeProbe:
        value = self._client.evaluate_earth("""(() => ({title:document.title,url:location.href,readyState:document.readyState,canvasCount:document.querySelectorAll('canvas').length,customElementNames:[...document.querySelectorAll('*')].map(e=>e.localName).filter(n=>n&&n.includes('-')).filter((n,i,v)=>v.indexOf(n)===i).sort().slice(0,100)}))()""")
        if not isinstance(value, dict): raise RuntimeError("Google Earth runtime probe returned an unexpected value")
        names=value.get("customElementNames"); names=names if isinstance(names,list) else []
        return EarthRuntimeProbe(str(value.get("title","")),str(value.get("url","")),str(value.get("readyState","")),int(value.get("canvasCount",0)),tuple(str(n) for n in names))

    def inspect_runtime(self) -> EarthRuntimeInspection:
        value=self._client.evaluate_earth(r"""(() => {const safeKeys=v=>{if(v==null)return[];try{return Object.getOwnPropertyNames(v).sort().slice(0,80)}catch(_){return[]}};const describe=name=>{let v;try{v=window[name]}catch(_){return{name,type:'unreadable',constructorName:'',keys:[]}}let c='';try{c=v?.constructor?.name||''}catch(_){}return{name,type:typeof v,constructorName:c,keys:safeKeys(v)}};const candidates=Object.getOwnPropertyNames(window).filter(n=>/earth|camera|wasm/i.test(n)).filter(n=>!/^module\$contents\$google3\$third_party\$javascript\$angular2/.test(n)).sort().slice(0,120);const canvas=document.querySelector('canvas'),M=window.Module;return{earthWasmStarted:typeof window.earthWasmStarted==='boolean'?window.earthWasmStarted:null,modulePresent:M!=null,moduleKeys:safeKeys(M),canvas:canvas?{width:Number(canvas.width)||0,height:Number(canvas.height)||0,clientWidth:Number(canvas.clientWidth)||0,clientHeight:Number(canvas.clientHeight)||0}:null,globals:candidates.map(describe)}})()""")
        if not isinstance(value,dict): raise RuntimeError("Google Earth runtime inspection returned an unexpected value")
        objects=[]
        for item in value.get("globals",[]) if isinstance(value.get("globals"),list) else []:
            if isinstance(item,dict):
                keys=item.get("keys"); objects.append(EarthRuntimeObject(str(item.get("name","")),str(item.get("type","")),str(item.get("constructorName","")),tuple(str(k) for k in keys) if isinstance(keys,list) else ()))
        canvas=value.get("canvas") if isinstance(value.get("canvas"),dict) else {}
        def oi(name):
            raw=canvas.get(name); return int(raw) if isinstance(raw,(int,float)) else None
        wasm=value.get("earthWasmStarted"); wasm=wasm if isinstance(wasm,bool) else None; mk=value.get("moduleKeys")
        return EarthRuntimeInspection(wasm,bool(value.get("modulePresent",False)),tuple(str(k) for k in mk) if isinstance(mk,list) else (),oi("width"),oi("height"),oi("clientWidth"),oi("clientHeight"),tuple(objects))

    def inspect_module_hooks(self) -> tuple[EarthModuleHook,...]:
        value=self._client.evaluate_earth("""(() => {const M=window.Module;if(!M)return[];const names=['ReceiveViewModelCommand','ResizeViewport','onViewportResized','ccall','cwrap','canvas','ctx','labelRenderer','earth-ready','_initialize','_main'];return names.map(name=>{let v;try{v=M[name]}catch(_){v=undefined}let c='';try{c=v?.constructor?.name||''}catch(_){}let keys=[];try{if(v!=null)keys=Object.getOwnPropertyNames(v).sort().slice(0,50)}catch(_){}let sourcePreview='';if(typeof v==='function'){try{sourcePreview=Function.prototype.toString.call(v).slice(0,500)}catch(_){}}let embindArgCount=null;if(typeof v==='function'){try{embindArgCount=Number.isInteger(v.argCount)?v.argCount:null}catch(_){}}return{name,type:typeof v,constructorName:c,arity:typeof v==='function'?v.length:null,embindArgCount,sourcePreview,keys}})})()""")
        if not isinstance(value,list): return ()
        hooks=[]
        for item in value:
            if not isinstance(item,dict): continue
            ar=item.get("arity"); ea=item.get("embindArgCount"); keys=item.get("keys"); hooks.append(EarthModuleHook(str(item.get("name","")),str(item.get("type","")),str(item.get("constructorName","")),int(ar) if isinstance(ar,(int,float)) else None,int(ea) if isinstance(ea,(int,float)) else None,str(item.get("sourcePreview","")),tuple(str(k) for k in keys) if isinstance(keys,list) else ()))
        return tuple(hooks)

    def install_command_trace(self) -> bool:
        value=self._client.evaluate_earth("""(() => {const M=window.Module;if(!M||typeof M.ReceiveViewModelCommand!=='function')return false;if(window.__orcEarthCommandTrace?.installed)return true;const original=M.ReceiveViewModelCommand,trace={installed:true,original,calls:[]};const describe=arg=>{let constructorName='',keys=[],preview='';try{constructorName=arg?.constructor?.name||''}catch(_){}try{if(arg!=null)keys=Object.getOwnPropertyNames(arg).slice(0,40)}catch(_){}try{if(typeof arg==='string')preview=arg.slice(0,500);else if(arg instanceof Uint8Array)preview=Array.from(arg.slice(0,80)).join(',');else if(arg instanceof ArrayBuffer)preview=Array.from(new Uint8Array(arg).slice(0,80)).join(',');else preview=String(arg).slice(0,500)}catch(_){}return{type:typeof arg,constructorName,keys,preview,length:typeof arg?.length==='number'?arg.length:null,byteLength:typeof arg?.byteLength==='number'?arg.byteLength:null}};const wrapped=function(...args){try{trace.calls.push({time:Date.now(),args:args.map(describe)});if(trace.calls.length>100)trace.calls.shift()}catch(_){}return original.apply(this,args)};try{wrapped.argCount=original.argCount}catch(_){}M.ReceiveViewModelCommand=wrapped;window.__orcEarthCommandTrace=trace;return true})()""")
        return value is True

    def read_command_trace(self) -> tuple[dict[str,Any],...]:
        value=self._client.evaluate_earth("(() => window.__orcEarthCommandTrace?.calls || [])()")
        return tuple(item for item in value if isinstance(item,dict)) if isinstance(value,list) else ()

    def clear_command_trace(self) -> None:
        self._client.evaluate_earth("(() => {const t=window.__orcEarthCommandTrace;if(t)t.calls.length=0;return true})()")

    def inspect_globals(self, *, keywords: tuple[str,...] = ("earth","camera","map","scene","view")) -> tuple[str,...]:
        encoded=repr([k.lower() for k in keywords]); value:Any=self._client.evaluate_earth("(() => {const needles="+encoded+";return Object.getOwnPropertyNames(window).filter(n=>needles.some(x=>n.toLowerCase().includes(x))).sort().slice(0,200)})()")
        return tuple(str(n) for n in value) if isinstance(value,list) else ()

    def set_view(self, view: EarthCameraView) -> bool:
        """Feed ORC position into Chromium's geolocation provider for Earth tracking."""
        try:
            self._client.set_geolocation_override(
                view.latitude_deg,
                view.longitude_deg,
                accuracy_m=5.0,
            )
        except (OSError, RuntimeError, ValueError):
            return False
        return True
