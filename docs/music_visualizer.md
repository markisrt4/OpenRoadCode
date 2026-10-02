# Music visualizer

The refreshed visualizer uses shared PCM capture and FFT analysis for the native
ORC UI and WebUi. Frontends render analysis state; Android permissions and audio
capture stay in the platform backend.

## ORC UI

Run `./runOrcUi`, then open **Media → Music Visualizer**. ORC embeds the
browser WebGL renderer inside its Media screen, retaining the shared ORC
navigation and shell. The local HTTP host is created by composition; no separate
WebUi process or service configuration is required.

The renderer offers 13 presets: Frequency Tunnel, Neon Ribbon, Spectrum Field,
Plasma Bloom, Kaleidoscope, Star Warp, Electric Rings, Dancing Planets, Star Dance,
Neon Instruments, Electric Freeway, Explosion Field, and Prismatic Spectrum.
Use the sensitivity slider to adjust response and FULL SCREEN to expand the
visualization. Browser Microphone is always offered; Chromium requests permission
when you press START AUDIO. Linux System Audio is offered when `pw-record` is
installed. Android Playback is offered on Termux/Android and consumes the local
bridge stream at `http://127.0.0.1:8768/stream`; grant playback-capture consent in
the bridge app first. Capture-restricted applications may not provide audio.

For PipeWire playback monitoring, set
`OPENROAD_MUSIC_VISUALIZER_PIPEWIRE_TARGET` to the appropriate monitor node.
`OPENROAD_MUSIC_VISUALIZER_SOURCE=pipewire` or `android-playback` preselects an
available input. Capture begins only when START AUDIO is pressed. STOP and leaving
the screen release capture; ORC shutdown closes Chromium and the local server.
CALIBRATE, FINISH, and CLEAR manage the shared ambient-noise profile.
`OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE` defaults to 2048 and must be at least 2048.

Chromium, `xdotool`, Flask, and NumPy are included in the updated desktop/Termux
setup. Existing desktop installs can refresh Python dependencies with
`./scripts/installers/install_python_env.sh desktop-ui` and host dependencies
with the normal desktop/browser setup.

The eight-mode Tk renderer remains an explicit fallback via
`OPENROAD_MUSIC_VISUALIZER_RENDERER=tk`; its default input is simulation.

## WebUi

Run `python -m apps.webUi.main`, then open **Media → Visualizer**. Source discovery
always offers browser PCM; PipeWire is offered when `pw-record` is installed.
Android playback is offered on Android or when
`OPENROADCODE_ANDROID_PLAYBACK=1` is set for an integration environment.

Browser audio uses microphone permission and requires a browser context that
allows `getUserMedia` (normally HTTPS or localhost). Browser code transports
PCM16; the Python analyzer owns FFT, percussion estimates, and calibration. The
WebGL panel provides 13 presets and the percussion panel renders shared analysis.
Source selection and calibration use the `/api/audio-analysis/` HTTP API.

Music-reactive lighting is optional and reports unavailable without a configured
backend. `OPENROADCODE_WEB_DUMMY_LIGHTING=1` enables the dummy backend for software
checks. Song recognition is optional and requires `ACRCLOUD_HOST`,
`ACRCLOUD_ACCESS_KEY`, and `ACRCLOUD_ACCESS_SECRET`, supplied outside source
control. Do not put credentials in scripts or configuration committed to Git.

## Dependencies and validation

NumPy is required by the native analyzer and is included in desktop-ui and web-ui
Python dependencies. Termux installs `python-numpy` with its package manager and
uses a virtual environment with system packages visible.

Run the automated unit and integration suites from the repository root:

```bash
python scripts/run_tests.py all
```

Hardware component checks remain separate: confirm live PipeWire monitor audio
on Linux, Android playback consent and streaming on the phone, and browser
microphone/WebGL behavior in the target browser. Passing synthetic-PCM tests does
not verify those device and permission paths.

## Architecture and resource ownership

Media composition selects presentation and owns its runtime. The default uses the
reusable `BrowserMediaScreen`, an ORC-selected `MusicVisualizerBrowser` adapter,
and the existing shared WebGL assets. The adapter owns only the local HTTP host
and browser lifecycle; `MusicAnalysisSession` owns audio capture and analysis.
HTTP routes and the embedded page live under `frontends/web/audio_analysis` and
serve the same semantic analyzer used by WebUi. The Tk fallback still consumes
`MusicVisualizerControlIf`, with its capture/calibration worker in the controller.
Screens choose no backends and composition closes their resources.
