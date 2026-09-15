# System Controllers

`controllers/system` owns toolkit-independent system behavior that is triggered by UI contracts but implemented using host facilities.

`SystemLifecycleController` records restart or poweroff intent when requested by a UI and deliberately defers the host action until application composition has finished normal resource cleanup. The UI contract lives in `ui.system`; operating-system process and power-management details do not.
