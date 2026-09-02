# Ethernet Interface Design Description (IDD)

This document is the project-wide registry for default IP ports used by OpenRoadCode software, development utilities, and directly managed companion services.

The registry covers ports that OpenRoadCode assigns, binds, connects to, or explicitly configures. Generic outbound Internet traffic such as HTTPS requests to Spotify, YouTube, Open-Meteo, package repositories, and other third-party services is outside this IDD because those remote ports are not owned by OpenRoadCode.

Unless a row explicitly says otherwise, the values below are defaults and may be overridden by runtime configuration, environment variables, command-line arguments, or external-service configuration.

## Port registry

| Port | Default address / endpoint | Owner | Role | Transport | Application protocol | Unit test(s) | Scope / notes |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 2947 | `127.0.0.1:2947` | `gpsd` | GNSS data service consumed by navigation and weather location providers | TCP | gpsd JSON protocol | No direct unit test located | Current Linux/Raspberry Pi runtime default. Configured by `services.navigation.inputs.gps` in `config/runtime.toml`. |
| 4532 | `127.0.0.1:4532` | SDR++ Rigctl Server | Radio tuning/control endpoint consumed by OpenRoadCode radio controllers | TCP | Hamlib rigctl text protocol | No direct unit test located | Current runtime default in `config/runtime.toml`; SDR++ is the server. |
| 4533 | `127.0.0.1:4533` | OpenRoadCode SDR++ remote-control module | Higher-level SDR++ UI/application control | TCP | OpenRoadCode line-oriented UTF-8 command/response protocol | No direct unit test located | Dedicated SDR++ remote-control endpoint. |
| 5000 | `0.0.0.0:5000` | `apps/webUi` | Main OpenRoadCode web frontend | TCP | HTTP (Flask) | No direct unit test located | Current `apps/webUi/main.py` default; override with `OPENROADCODE_WEB_HOST` / `OPENROADCODE_WEB_PORT`. |
| 5556 | `tcp://0.0.0.0:5556` broker bind; clients normally use `tcp://127.0.0.1:5556` | OpenRoadCode ZeroMQ broker | Broker ingress for application/service publishers | TCP | ZeroMQ XSUB | No direct unit test located | Current message-bus publisher endpoint. The broker owns the listening socket; producers connect. |
| 5557 | `tcp://0.0.0.0:5557` broker bind; clients normally use `tcp://127.0.0.1:5557` | OpenRoadCode ZeroMQ broker | Broker egress for subscribers | TCP | ZeroMQ XPUB | No direct unit test located | Current message-bus subscriber endpoint. The broker owns the listening socket; applications and the map renderer connect. |
| 5560 | `tcp://127.0.0.1:5560` | Navigation producer service | Acknowledged navigation command endpoint | TCP | ZeroMQ request/reply | No direct unit test located | Current `services.navigation.command_endpoint` default. |
| 5902 | `*:5902` for default display `:2` | VNC server launched by `scripts/runtime/start_vnc_server.sh` | Remote graphical desktop | TCP | RFB / VNC | No direct unit test located | Optional development/runtime utility. Port is `5900 + DISPLAY_NUM`; the script defaults to display `2` and explicitly permits non-localhost connections. |
| 8002 | `http://127.0.0.1:8002` | Valhalla service | Offline route-planning API | TCP | HTTP / Valhalla JSON API | No direct unit test located | Current navigation route-planning default in `config/runtime.toml`. |
| 8081 | `127.0.0.1:8081` | tar1090 presentation server | ADS-B aircraft web presentation | TCP | HTTP | No direct unit test located | Termux/runit default. `TAR1090_PORT` can override it. |
| 8501 | `127.0.0.1:8501` client URL | Weather dashboard / Streamlit | Weather dashboard web application | TCP | Streamlit HTTP/WebSocket | No direct unit test located | Default in `WeatherDashLauncher` / `StreamlitLauncher`. Streamlit owns the server process. |
| 8765 | `127.0.0.1:8765` | CarUI browser position source | Browser-provided geographic position for development | TCP | HTTP + JSON | [browser position source](../controllers/navigation/unit_test/test_browser_position_source.py); [position source factory](../apps/carUi/unit_test/test_position_source_factory.py) | Development/application-owned server. Configurable with `CARUI_BROWSER_POSITION_HOST` / `CARUI_BROWSER_POSITION_PORT`. |
| 8766 | `http://127.0.0.1:8766` | OpenRoadCode Android sensor bridge | Android location/IMU/sensor bridge consumed by Termux runtime | TCP | HTTP + JSON/NDJSON | No direct unit test located | Dedicated Android sensor bridge port. |
| 8767 | `127.0.0.1:8767` | Navigation `BrowserMotionSource` | Browser DeviceMotion development input | TCP | HTTP + JSON | No direct unit test located | Dedicated browser-motion development/component port. |
| 8768 | `127.0.0.1:8768` | `YouTubeMusicVideo` local player server | Serves the temporary local YouTube player page and close callback | TCP | HTTP | No direct unit test located | Dedicated transient music-video player port; listener exists only while playback is active. |
| 8888 | `127.0.0.1:8888/callback` | OpenRoadCode OAuth redirect server | Local browser OAuth callback, including Spotify authentication | TCP | HTTP / OAuth 2.0 loopback redirect | No direct unit test located | Transient authentication listener rather than a long-lived service. |
| 35000 | `127.0.0.1:35000` | OpenRoadCode Android Bluetooth SPP bridge | Raw ELM327 stream consumed by the Termux automotive service | TCP | Raw TCP carrying ELM327 ASCII command/response data | No direct unit test located | Current Termux automotive default. Android owns the Bluetooth SPP connection; OpenRoadCode consumes the proxied stream. |

`No direct unit test located` means the repository audit did not identify a unit test that directly exercises that listener or port. It does not mean the owning subsystem has no unit, integration, or component-test coverage. Links in this column deliberately point only to unit tests that directly cover the documented interface rather than merely testing nearby code.

## Port ownership rules

A fixed port is part of an interface contract even when it is bound only to loopback. New cross-process listeners and fixed remote endpoints should therefore be added to this registry in the same change that introduces them.

The process that binds a listening socket is the port owner. Clients should consume the owning subsystem's configured endpoint rather than quietly inventing a second default. When a third-party process is the server, such as `gpsd`, Valhalla, SDR++, Streamlit, or VNC, the **Owner** column names that process while the notes identify the OpenRoadCode configuration that depends on it.

Loopback-only defaults should remain loopback-only unless remote access is an intentional, reviewed part of the design. `0.0.0.0` / wildcard listeners deserve particular care because they can be reachable from the vehicle LAN or another connected network depending on host firewall and routing policy.

## Local application port allocation

The adjacent `8765`-`8768` range is intentionally allocated by function so independently enabled components do not compete for a socket:

1. `8765` - CarUI browser position source;
2. `8766` - Android sensor bridge;
3. `8767` - navigation browser motion source; and
4. `8768` - YouTube music-video local player.

These defaults may still be overridden where the owning component exposes configuration, but a new component must not reuse one of these defaults simply because it happens not to be running during development. That particular form of optimism is how the original collision arrived.

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
- `protocols/sdrpp_remote_control/client.py`

When code and this document disagree, treat the mismatch as a documentation defect or an undocumented interface change and reconcile both in the same pull request.
