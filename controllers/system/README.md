# System Controllers

`controllers/system` owns toolkit-independent system behavior that is triggered by UI contracts but implemented using host facilities.

`SystemLifecycleController` records restart or poweroff intent when requested by a UI and deliberately defers the host action until application composition has finished normal resource cleanup. The UI contract lives in `ui.system`; operating-system process and power-management details do not.

Deferred requests, cancellation, dispatch, unsupported actions, and failures use
`runtime.host` structured events with one operation ID from request to dispatch.
Executable paths, arguments, and raw errors are excluded. A dispatch event does
not confirm that poweroff or replacement UI startup completed. See the
[runtime logging guide](../../common/logging/README.md#runtime-and-service-management).
