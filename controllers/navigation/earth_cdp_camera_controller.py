# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Preferred Google Earth camera controller using Chromium DevTools."""

from __future__ import annotations

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

    def trigger_my_location(self) -> bool:
        """Replay the My Location command observed from Google's own Earth UI."""
        value = self._client.evaluate_earth(
            """(() => {
                const M = window.Module;
                if (!M || typeof M.ReceiveViewModelCommand !== 'function') return false;
                M.ReceiveViewModelCommand(
                    'earth.mylocation.MyLocationViewModelCommand',
                    new Uint8Array([18, 0])
                );
                return true;
            })()"""
        )
        return value is True

    def probe_runtime(self) -> EarthRuntimeProbe:
        value = self._client.evaluate_earth(
            """(() => ({
                title: document.title,
                url: location.href,
                readyState: document.readyState,
                canvasCount: document.querySelectorAll('canvas').length,
                customElementNames: [...document.querySelectorAll('*')]
                    .map(element => element.localName)
                    .filter(name => name && name.includes('-'))
                    .filter((name, index, values) => values.indexOf(name) === index)
                    .sort().slice(0, 100)
            }))()"""
        )
        if not isinstance(value, dict):
            raise RuntimeError("Google Earth runtime probe returned an unexpected value")
        names = value.get("customElementNames")
        if not isinstance(names, list): names = []
        return EarthRuntimeProbe(str(value.get("title", "")), str(value.get("url", "")),
            str(value.get("readyState", "")), int(value.get("canvasCount", 0)), tuple(str(n) for n in names))

    def inspect_runtime(self) -> EarthRuntimeInspection:
        value = self._client.evaluate_earth(r"""(() => {
            const safeKeys = value => { if (value == null) return []; try { return Object.getOwnPropertyNames(value).sort().slice(0,80); } catch (_) { return []; } };
            const describe = name => { let value; try { value=window[name]; } catch (_) { return {name,type:'unreadable',constructorName:'',keys:[]}; }
                let constructorName=''; try { constructorName=value?.constructor?.name||''; } catch (_) {}
                return {name,type:typeof value,constructorName,keys:safeKeys(value)}; };
            const candidates=Object.getOwnPropertyNames(window).filter(name=>/earth|camera|wasm/i.test(name))
                .filter(name=>!/^module\$contents\$google3\$third_party\$javascript\$angular2/.test(name)).sort().slice(0,120);
            const canvas=document.querySelector('canvas'); const moduleValue=window.Module;
            return {earthWasmStarted:typeof window.earthWasmStarted==='boolean'?window.earthWasmStarted:null,
                modulePresent:moduleValue!=null,moduleKeys:safeKeys(moduleValue),
                canvas:canvas?{width:Number(canvas.width)||0,height:Number(canvas.height)||0,clientWidth:Number(canvas.clientWidth)||0,clientHeight:Number(canvas.clientHeight)||0}:null,
                globals:candidates.map(describe)};
        })()""")
        if not isinstance(value, dict): raise RuntimeError("Google Earth runtime inspection returned an unexpected value")
        objects=[]
        for item in value.get("globals",[]) if isinstance(value.get("globals"),list) else []:
            if isinstance(item,dict):
                keys=item.get("keys")
                objects.append(EarthRuntimeObject(str(item.get("name","")),str(item.get("type","")),str(item.get("constructorName","")),tuple(str(k) for k in keys) if isinstance(keys,list) else ()))
        canvas=value.get("canvas") if isinstance(value.get("canvas"),dict) else {}
        def oi(name):
            raw=canvas.get(name); return int(raw) if isinstance(raw,(int,float)) else None
        wasm=value.get("earthWasmStarted"); wasm=wasm if isinstance(wasm,bool) else None
        mk=value.get("moduleKeys")
        return EarthRuntimeInspection(wasm,bool(value.get("modulePresent",False)),tuple(str(k) for k in mk) if isinstance(mk,list) else (),oi("width"),oi("height"),oi("clientWidth"),oi("clientHeight"),tuple(objects))

    def inspect_module_hooks(self) -> tuple[EarthModuleHook, ...]:
        value=self._client.evaluate_earth("""(() => { const M=window.Module;if(!M)return[];
            const names=['ReceiveViewModelCommand','ResizeViewport','onViewportResized','ccall','cwrap','canvas','ctx','labelRenderer','earth-ready','_initialize','_main'];
            return names.map(name=>{let value;try{value=M[name]}catch(_){value=undefined}let constructorName='';try{constructorName=value?.constructor?.name||''}catch(_){}
            let keys=[];try{if(value!=null)keys=Object.getOwnPropertyNames(value).sort().slice(0,50)}catch(_){}let sourcePreview='';if(typeof value==='function'){try{sourcePreview=Function.prototype.toString.call(value).slice(0,500)}catch(_){}}
            let embindArgCount=null;if(typeof value==='function'){try{embindArgCount=Number.isInteger(value.argCount)?value.argCount:null}catch(_){}}
            return{name,type:typeof value,constructorName,arity:typeof value==='function'?value.length:null,embindArgCount,sourcePreview,keys};});})()""")
        if not isinstance(value,list): return ()
        hooks=[]
        for item in value:
            if not isinstance(item,dict): continue
            ar=item.get("arity"); ea=item.get("embindArgCount"); keys=item.get("keys")
            hooks.append(EarthModuleHook(str(item.get("name","")),str(item.get("type","")),str(item.get("constructorName","")),int(ar) if isinstance(ar,(int,float)) else None,int(ea) if isinstance(ea,(int,float)) else None,str(item.get("sourcePreview","")),tuple(str(k) for k in keys) if isinstance(keys,list) else ()))
        return tuple(hooks)

    def install_command_trace(self) -> bool:
        value=self._client.evaluate_earth("""(() => {const M=window.Module;if(!M||typeof M.ReceiveViewModelCommand!=='function')return false;if(window.__orcEarthCommandTrace?.installed)return true;
            const original=M.ReceiveViewModelCommand;const trace={installed:true,original,calls:[]};const describe=arg=>{let constructorName='',keys=[],preview='';try{constructorName=arg?.constructor?.name||''}catch(_){}try{if(arg!=null)keys=Object.getOwnPropertyNames(arg).slice(0,40)}catch(_){}
            try{if(typeof arg==='string')preview=arg.slice(0,500);else if(arg instanceof Uint8Array)preview=Array.from(arg.slice(0,80)).join(',');else if(arg instanceof ArrayBuffer)preview=Array.from(new Uint8Array(arg).slice(0,80)).join(',');else preview=String(arg).slice(0,500)}catch(_){}
            return{type:typeof arg,constructorName,keys,preview,length:typeof arg?.length==='number'?arg.length:null,byteLength:typeof arg?.byteLength==='number'?arg.byteLength:null};};
            const wrapped=function(...args){try{trace.calls.push({time:Date.now(),args:args.map(describe)});if(trace.calls.length>100)trace.calls.shift()}catch(_){}return original.apply(this,args)};try{wrapped.argCount=original.argCount}catch(_){}M.ReceiveViewModelCommand=wrapped;window.__orcEarthCommandTrace=trace;return true;})()""")
        return value is True

    def read_command_trace(self) -> tuple[dict[str, Any], ...]:
        value=self._client.evaluate_earth("(() => window.__orcEarthCommandTrace?.calls || [])()")
        return tuple(item for item in value if isinstance(item,dict)) if isinstance(value,list) else ()

    def clear_command_trace(self) -> None:
        self._client.evaluate_earth("(() => { const t=window.__orcEarthCommandTrace;if(t)t.calls.length=0;return true; })()")

    def inspect_globals(self, *, keywords: tuple[str, ...] = ("earth","camera","map","scene","view")) -> tuple[str, ...]:
        encoded=repr([k.lower() for k in keywords]); value:Any=self._client.evaluate_earth("(() => { const needles="+encoded+";return Object.getOwnPropertyNames(window).filter(name=>needles.some(needle=>name.toLowerCase().includes(needle))).sort().slice(0,200);})()")
        return tuple(str(name) for name in value) if isinstance(value,list) else ()

    def set_view(self, view: EarthCameraView) -> bool:
        del view
        return False
