# Application Launchers

The `apps.launchers` package starts, stops, and monitors external applications
used by higher-level UIs.

## Responsibilities

Launchers may:

- start an owned subprocess;
- set the X11 display environment;
- wait for an external service to become ready;
- open a browser kiosk;
- stop owned subprocesses;
- perform display-scoped fallback cleanup.

Launchers must not contain panel or Tk widget logic.

## Interface

Every launcher implements:

```python
launch(remote_display, set_status=None)
stop(remote_display, set_status=None)
toggle(remote_display, set_status=None) -> bool
is_running() -> bool
```

`toggle()` returns `True` when the application is running after the operation
and `False` when it has been stopped.

## Implementations

- `BrowserKioskLauncher`: Chromium or Chrome kiosk window.
- `StreamlitLauncher`: Streamlit server plus kiosk browser.
- `WeatherDashLauncher`: configured Streamlit launcher for
  `apps/weatherDash/main.py`.
- `SDRPPLauncher`: SDR++ plus RigCTL readiness checking.
- `ADSBLauncher`: readsb service plus tar1090 kiosk browser.
- `AppLauncherStub`: deterministic test implementation.

## Process ownership

A launcher first terminates the exact subprocess it created. A display-scoped
pattern search is used only as fallback cleanup for processes that survived a
previous application run.

Avoid global `pkill -f` cleanup because it can terminate unrelated user
processes.

ADS-B and Weather belong to the same exclusive auxiliary-dashboard browser
group. Launching either dashboard closes the other browser window on that X
display, while leaving independently managed backend services available.

## Runtime dependencies

Browser kiosk support requires one of:

```text
chromium-browser
chromium
google-chrome
```

SDR++ fullscreen requests require:

```text
wmctrl
```

Streamlit launchers require the Python package:

```bash
python3 -m pip install streamlit
```

`StreamlitLauncher.prepare()` starts the server and waits for HTTP readiness
without opening a browser, allowing frontends to warm dashboards in a daemon
worker after their primary startup path completes. `close_browser()` hides the
dashboard without discarding that warmed server; `stop()` releases both.

ADS-B launch requires a systemd-managed `readsb` service and a reachable
tar1090 installation.

On hardware-free development hosts, ADS-B may still open a reachable tar1090
dashboard without live receiver data. Reopening a dashboard tile raises its
existing browser window instead of interpreting the action as a request to
stop a hidden kiosk; the Return overlay owns dashboard shutdown.

## Testing

Use `AppLauncherStub` when launcher behavior itself is irrelevant to a
consumer test.

Process launchers should be tested with mocked `subprocess`, `shutil.which`,
and socket calls rather than starting real desktop applications in unit tests.
