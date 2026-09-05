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
    """Harmless page-level facts used to verify the Earth CDP connection."""

    title: str
    url: str
    ready_state: str
    canvas_count: int
    custom_element_names: tuple[str, ...]


@dataclass(frozen=True)
class EarthRuntimeObject:
    """Shallow description of one potentially useful Earth runtime global."""

    name: str
    value_type: str
    constructor_name: str
    keys: tuple[str, ...]


@dataclass(frozen=True)
class EarthModuleHook:
    """Read-only description of a selected Emscripten Module member."""

    name: str
    value_type: str
    constructor_name: str
    arity: int | None
    embind_arg_count: int | None
    source_preview: str
    keys: tuple[str, ...]


@dataclass(frozen=True)
class EarthRuntimeInspection:
    """Targeted facts about Earth's JS/WASM boundary and render canvas."""

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

    def probe_runtime(self) -> EarthRuntimeProbe:
        """Prove Runtime.evaluate works without changing Google Earth state."""
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
                    .sort()
                    .slice(0, 100)
            }))()"""
        )
        if not isinstance(value, dict):
            raise RuntimeError("Google Earth runtime probe returned an unexpected value")
        names = value.get("customElementNames")
        if not isinstance(names, list):
            names = []
        return EarthRuntimeProbe(
            title=str(value.get("title", "")),
            url=str(value.get("url", "")),
            ready_state=str(value.get("readyState", "")),
            canvas_count=int(value.get("canvasCount", 0)),
            custom_element_names=tuple(str(name) for name in names),
        )

    def inspect_runtime(self) -> EarthRuntimeInspection:
        """Inspect likely Earth camera/WASM globals without invoking them."""
        value = self._client.evaluate_earth(
            r"""(() => {
                const safeKeys = value => {
                    if (value === null || value === undefined) return [];
                    try { return Object.getOwnPropertyNames(value).sort().slice(0, 80); }
                    catch (_) { return []; }
                };
                const describe = name => {
                    let value;
                    try { value = window[name]; }
                    catch (_) { return {name, type: 'unreadable', constructorName: '', keys: []}; }
                    let constructorName = '';
                    try { constructorName = value?.constructor?.name || ''; }
                    catch (_) {}
                    return {
                        name,
                        type: typeof value,
                        constructorName,
                        keys: safeKeys(value),
                    };
                };
                const candidates = Object.getOwnPropertyNames(window)
                    .filter(name => /earth|camera|wasm/i.test(name))
                    .filter(name => !/^module\$contents\$google3\$third_party\$javascript\$angular2/.test(name))
                    .sort()
                    .slice(0, 120);
                const canvas = document.querySelector('canvas');
                const moduleValue = window.Module;
                return {
                    earthWasmStarted: typeof window.earthWasmStarted === 'boolean'
                        ? window.earthWasmStarted : null,
                    modulePresent: moduleValue !== undefined && moduleValue !== null,
                    moduleKeys: safeKeys(moduleValue),
                    canvas: canvas ? {
                        width: Number(canvas.width) || 0,
                        height: Number(canvas.height) || 0,
                        clientWidth: Number(canvas.clientWidth) || 0,
                        clientHeight: Number(canvas.clientHeight) || 0,
                    } : null,
                    globals: candidates.map(describe),
                };
            })()"""
        )
        if not isinstance(value, dict):
            raise RuntimeError("Google Earth runtime inspection returned an unexpected value")

        raw_globals = value.get("globals")
        objects: list[EarthRuntimeObject] = []
        if isinstance(raw_globals, list):
            for item in raw_globals:
                if not isinstance(item, dict):
                    continue
                raw_keys = item.get("keys")
                keys = tuple(str(key) for key in raw_keys) if isinstance(raw_keys, list) else ()
                objects.append(
                    EarthRuntimeObject(
                        name=str(item.get("name", "")),
                        value_type=str(item.get("type", "")),
                        constructor_name=str(item.get("constructorName", "")),
                        keys=keys,
                    )
                )

        canvas = value.get("canvas")
        if not isinstance(canvas, dict):
            canvas = {}
        wasm_started = value.get("earthWasmStarted")
        if not isinstance(wasm_started, bool):
            wasm_started = None
        raw_module_keys = value.get("moduleKeys")
        module_keys = tuple(str(key) for key in raw_module_keys) if isinstance(raw_module_keys, list) else ()

        def optional_int(name: str) -> int | None:
            raw = canvas.get(name)
            return int(raw) if isinstance(raw, (int, float)) else None

        return EarthRuntimeInspection(
            earth_wasm_started=wasm_started,
            module_present=bool(value.get("modulePresent", False)),
            module_keys=module_keys,
            canvas_width=optional_int("width"),
            canvas_height=optional_int("height"),
            canvas_client_width=optional_int("clientWidth"),
            canvas_client_height=optional_int("clientHeight"),
            globals=tuple(objects),
        )

    def inspect_module_hooks(self) -> tuple[EarthModuleHook, ...]:
        """Describe selected Earth Module bridge members without calling them."""
        value = self._client.evaluate_earth(
            """(() => {
                const moduleValue = window.Module;
                if (!moduleValue) return [];
                const names = [
                    'ReceiveViewModelCommand',
                    'ResizeViewport',
                    'onViewportResized',
                    'ccall',
                    'cwrap',
                    'canvas',
                    'ctx',
                    'labelRenderer',
                    'earth-ready',
                    '_initialize',
                    '_main'
                ];
                return names.map(name => {
                    let value;
                    try { value = moduleValue[name]; }
                    catch (_) { value = undefined; }
                    let constructorName = '';
                    try { constructorName = value?.constructor?.name || ''; }
                    catch (_) {}
                    let keys = [];
                    try {
                        if (value !== null && value !== undefined)
                            keys = Object.getOwnPropertyNames(value).sort().slice(0, 50);
                    } catch (_) {}
                    let sourcePreview = '';
                    if (typeof value === 'function') {
                        try { sourcePreview = Function.prototype.toString.call(value).slice(0, 500); }
                        catch (_) {}
                    }
                    let embindArgCount = null;
                    if (typeof value === 'function') {
                        try {
                            embindArgCount = Number.isInteger(value.argCount)
                                ? value.argCount : null;
                        } catch (_) {}
                    }
                    return {
                        name,
                        type: typeof value,
                        constructorName,
                        arity: typeof value === 'function' ? value.length : null,
                        embindArgCount,
                        sourcePreview,
                        keys,
                    };
                });
            })()"""
        )
        if not isinstance(value, list):
            return ()
        hooks: list[EarthModuleHook] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            raw_arity = item.get("arity")
            arity = int(raw_arity) if isinstance(raw_arity, (int, float)) else None
            raw_embind_arg_count = item.get("embindArgCount")
            embind_arg_count = (
                int(raw_embind_arg_count)
                if isinstance(raw_embind_arg_count, (int, float))
                else None
            )
            raw_keys = item.get("keys")
            keys = tuple(str(key) for key in raw_keys) if isinstance(raw_keys, list) else ()
            hooks.append(
                EarthModuleHook(
                    name=str(item.get("name", "")),
                    value_type=str(item.get("type", "")),
                    constructor_name=str(item.get("constructorName", "")),
                    arity=arity,
                    embind_arg_count=embind_arg_count,
                    source_preview=str(item.get("sourcePreview", "")),
                    keys=keys,
                )
            )
        return tuple(hooks)

    def inspect_globals(self, *, keywords: tuple[str, ...] = ("earth", "camera", "map", "scene", "view")) -> tuple[str, ...]:
        """Return matching top-level global names without invoking Earth internals."""
        encoded_keywords = repr([keyword.lower() for keyword in keywords])
        expression = (
            "(() => { const needles = "
            + encoded_keywords
            + "; return Object.getOwnPropertyNames(window)"
            ".filter(name => needles.some(needle => name.toLowerCase().includes(needle)))"
            ".sort().slice(0, 200); })()"
        )
        value: Any = self._client.evaluate_earth(expression)
        if not isinstance(value, list):
            return ()
        return tuple(str(name) for name in value)

    def set_view(self, view: EarthCameraView) -> bool:
        # Deliberately do not depend on undocumented Earth internals yet.
        # Runtime.evaluate is now available, but camera mutation stays disabled
        # until the runtime probe identifies a mechanism worth isolating here.
        del view
        return False
