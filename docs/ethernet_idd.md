# Ethernet Interface Design Description (IDD)

This document is the project-wide registry for default IP ports used by OpenRoadCode software, development utilities, and directly managed companion services.

The registry covers ports that OpenRoadCode assigns, binds, connects to, or explicitly configures. Generic outbound Internet traffic such as HTTPS requests to Spotify, YouTube, Open-Meteo, package repositories, and other third-party services is outside this IDD because those remote ports are not owned by OpenRoadCode.

Unless a row explicitly says otherwise, the values below are defaults and may be overridden by runtime configuration, environment variables, command-line arguments, or external-service configuration.

## Port registry

| Port | Default address / endpoint | Owner | Role | Transport | Application protocol | Scope / notes |
| ---: | --- | --- | --- | --- | --- | --- |
| 2947 | `127.0.0.1:2947` | `gpsd` | GNSS data service consumed by navigation and weather location providers | TCP | gpsd JSON protocol | Current Linux/Raspberry Pi runtime default. Configured by `services.navigation.inputs.gps` in `config/runtime.toml`. |
| 4532 | `127.0.0.1:4532` | SDR++ Rigctl Server | Radio tuning/control endpoint consumed by OpenRoadCode radio controllers | TCP | Hamlib rigctl text protocol | Current runtime default in `config/runtime.toml`; SDR++ is the server. |
| 4533 | `127.0.0.1:4533` | OpenRoadCode SDR++ remote-control module | Higher-level SDR++ UI/application control | TCP | OpenRoadCode line-oriented UTF-8 command/response protocol | **Branch-only:** `orcui-sdrpp-integration`. Not present on `master` as of the audit date. |
| 5000 | `0.0.0.0:5000` | `apps/webUi` | Main OpenRoadCode web frontend | TCP | HTTP (Flask) | Current `apps/webUi/main.py` default; override with `OPENROADCODE_WEB_HOST` / `OPENROADCODE_WEB_PORT`. |
| 5556 | `tcp://0.0.0.0:5556` broker bind; clients normally use `tcp://127.0.0.1:5556` | OpenRoadCode ZeroMQ broker | Broker ingress for application/service publishers | TCP | ZeroMQ XSUB | Current message-bus publisher endpoint. The broker owns the listening socket; producers connect. |
| 5557 | `tcp://0.0.0.0:5557` broker bind; clients normally use `tcp://127.0.0.1:5557` | OpenRoadCode ZeroMQ broker | Broker egress for subscribers | TCP | ZeroMQ XPUB | Current message-bus subscriber endpoint. The broker owns the listening socket; applications and the map renderer connect. |
| 5560 | `tcp://127.0.0.1:5560` | Navigation producer service | Acknowledged navigation command endpoint | TCP | ZeroMQ request/reply | Current `services.navigation.command_endpoint` default. |
| 5902 | `*:5902` for default display `:2` | VNC server launched by `scripts/runtime/start_vnc_server.sh` | Remote graphical desktop | TCP | RFB / VNC | Optional development/runtime utility. Port is `5900 + DISPLAY_NUM`; the script defaults to display `2` and explicitly permits non-localhost connections. |
| 8002 | `http://127.0.0.1:8002` | Valhalla service | Offline route-planning API | TCP | HTTP / Valhalla JSON API | Current navigation route-planning default in `config/runtime.toml`. |
| 8081 | `127.0.0.1:8081` | tar1090 presentation server | ADS-B aircraft web presentation | TCP | HTTP | Termux/runit default. `TAR1090_PORT` can override it. |
| 8501 | `127.0.0.1:8501` client URL | Weather dashboard / Streamlit | Weather dashboard web application | TCP | Streamlit HTTP/WebSocket | Default in `WeatherDashLauncher` / `StreamlitLauncher`. Streamlit owns the server process. |
| 8765 | `127.0.0.1:8765` | CarUI browser position source | Browser-provided geographic position for development | TCP | HTTP + JSON | Development/application-owned server. Configurable with `CARUI_BROWSER_POSITION_HOST` / `CARUI_BROWSER_POSITION_PORT`. |
| 8766 | `http://127.0.0.1:8766` | OpenRoadCode Android sensor bridge | Android location/IMU/sensor bridge consumed by Termux runtime | TCP | HTTP + JSON/NDJSON | Current Termux runtime default. **Conflicts with the other 8766 defaults below if run simultaneously.** |
| 8766 | `127.0.0.1:8766` | Navigation `BrowserMotionSource` | Browser DeviceMotion development input | TCP | HTTP + JSON | Development/component source. **Shares the default with the Android sensor bridge and YouTube music-video local server. Reconfigure before concurrent use.** |
| 8766 | `127.0.0.1:8766` | `YouTubeMusicVideo` local player server | Serves the temporary local YouTube player page and close callback | TCP | HTTP | Started only while music-video playback is active. **Shares the default with the Android sensor bridge and browser motion source. Reconfigure before concurrent use.** |
| 8888 | `127.0.0.1:8888/callback` | OpenRoadCode OAuth redirect server | Local browser OAuth callback, including Spotify authentication | TCP | HTTP / OAuth 2.0 loopback redirect | Transient authentication listener rather than a long-lived service. |
| 35000 | `127.0.0.1:35000` | OpenRoadCode Android Bluetooth SPP bridge | Raw ELM327 stream consumed by the Termux automotive service | TCP | Raw TCP carrying ELM327 ASCII command/response data | Current Termux automotive default. Android owns the Bluetooth SPP connection; OpenRoadCode consumes the proxied stream. |

## Port ownership rules

A fixed port is part of an interface contract even when it is bound only to loopback. New cross-process listeners and fixed remote endpoints should therefore be added to this registry in the same change that introduces them.

The process that binds a listening socket is the port owner. Clients should consume the owning subsystem's configured endpoint rather than quietly inventing a second default. When a third-party process is the server, such as `gpsd`, Valhalla, SDR++, Streamlit, or VNC, the **Owner** column names that process while the notes identify the OpenRoadCode configuration that depends on it.

Loopback-only defaults should remain loopback-only unless remote access is an intentional, reviewed part of the design. `0.0.0.0` / wildcard listeners deserve particular care because they can be reachable from the vehicle LAN or another connected network depending on host firewall and routing policy.

## Known default-port collision: 8766

Port `8766` currently has three independent default owners:

1. the Android sensor bridge used by the Termux runtime;
2. `services.navigation.browser_motion_source.BrowserMotionSource`; and
3. `controllers.video.youtube_music_video.YouTubeMusicVideo`.

Those roles cannot bind the same address and port simultaneously. The Android bridge is part of the active Termux runtime, while the browser-motion source is primarily a development/component path and the YouTube server is transient. Until the defaults are separated, any composition that enables more than one of them must override at least one port.

This collision is intentionally recorded here rather than hidden. An IDD is considerably more useful when it documents reality instead of providing a beautifully formatted alibi for it.

## Branch audit

Audit date: **2026-09-02**  
Baseline: `master` at `d07a92118c638150aa7838b891f145be2e927932`

All repository branches visible during the audit were compared with `master` for network-facing changes and fixed-port additions.

| Branch | Audit result |
| --- | --- |
| `master` | Baseline for the port registry above. |
| `android_sensor_bridge` | Fully behind `master`; no branch-only port. |
| `android-waydroid-frontend` | Diverged; map/Android frontend work adds no unique fixed port beyond existing message-bus/map dependencies. |
| `archive/bluetooth-integration-20260827` | Diverged archived Bluetooth/UI work; no unique fixed IP port. |
| `automotive` | Diverged automotive/UI work; no unique fixed IP port. |
| `bluetooth_dev` | Diverged BLE GATT work; Bluetooth transport only, no unique Ethernet/IP port. |
| `bluetooth-integration` | Diverged BLE/UI work; no unique fixed IP port. |
| `feature/telemetry-systemd` | Diverged runtime ownership work; no unique fixed port. |
| `fix/termux-runit-runtime-state` | Fully behind `master`; no branch-only port. |
| `game_launcher` | Diverged game-launcher work; no unique fixed port. |
| `integration/orc-ui-games` | Diverged ORC UI/game integration; no unique fixed port. |
| `music-visualizer` | Diverged audio/web work; no unique fixed port beyond interfaces already represented on `master` such as the OAuth callback. |
| `music-visualizer-refresh` | Diverged audio/web refresh; no unique fixed port. |
| `navigation-google-earth` | Diverged browser/Google Earth integration; no unique fixed local service port. |
| `orc-ui-shell` | Fully behind `master`; no branch-only port. |
| `orcui-sdrpp-integration` | **Adds branch-only TCP port 4533** for the OpenRoadCode SDR++ remote-control module. |
| `portable_router` | Diverged network-router work; manages interfaces/NAT and a `192.168.8.1/24` bench LAN but introduces no fixed OpenRoadCode application port. |
| `python3-dependencies-update` | Diverged legacy Qt/dependency work; no unique fixed port. |
| `termux_target` | Fully behind `master`; no branch-only port. |
| `text_input_device` | Diverged text-input/Valhalla work; remote text input is an in-process abstraction and adds no separate socket. Valhalla uses the existing route-planning interface. |
| `ui_interfaces` | Fully behind `master`; no branch-only port. |
| `ui-theme-css` | Diverged UI/automotive work; no unique fixed port. |

## Source-of-truth locations

The principal code/configuration locations behind this registry are:

- `config/runtime.toml`
- `config/runtime.termux.toml`
- `messaging/zeromq/endpoints.py`
- `services/navigation/endpoints.py`
- `services/navigation/browser_motion_source.py`
- `apps/carUi/runtime/browser_position_source.py`
- `apps/webUi/main.py`
- `apps/launchers/weather_dash_launcher.py`
- `apps/launchers/streamlit_launcher.py`
- `development/termux/setup_tar1090.sh`
- `scripts/runit/openroadcode-adsb/run`
- `scripts/runtime/start_vnc_server.sh`
- `protocols/rigctl/`
- `protocols/oauth/`
- `hardware_io/android/`
- `hardware_io/automotive/elm327/elm327_tcp_device.py`
- `controllers/video/youtube_music_video.py`
- branch `orcui-sdrpp-integration`: `protocols/sdrpp_remote_control/client.py`

When code and this document disagree, treat the mismatch as a documentation defect or an undocumented interface change and reconcile both in the same pull request.
