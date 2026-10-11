# Music visualizer

The refreshed visualizer uses shared PCM capture and FFT analysis for the native
ORC UI and WebUi. Frontends render analysis state; Android permissions and audio
capture stay in the platform backend.

## ORC UI

Run `./runOrcUi`, then open **Media → Music Visualizer**. ORC now defaults to
native OpenGL in its Tk Media screen, using the existing GLX backend shared with
the ECU renderer (including Termux/X11 compatibility). No browser process or local
HTTP server is created for this renderer.

The native picker offers nine distinct scenes: Frequency Tunnel, Spectrum Field,
Orbiting Planets, Electric Freeway, Explosion Field, Star Dance, Electric Rings,
Neon Ribbon, and Kaleidoscope. Frequency Tunnel sends spectrum-shaped rings
through a 3D tunnel, expanding and brightening on musical onsets. **Drum Kit**
switches the same GL surface to shaded drum shells, chrome rims, drumhead pulses,
two optional animated sticks, and wobbling cymbals. The camera starts much closer;
DRUM ZOOM adjusts the framing while preserving the kit on narrow surfaces.
Single/double kick layouts share the same capture and calibration. The **Beat response** slider changes visual pulse strength.
All capture, calibration, scene, kick, beat, zoom, and stick controls live in a
scrollable ORC-themed rail on the left; the GL surface fills the right side.
Selecting a scene immediately shows it without restarting capture. These native
scenes use their own GL geometry rather than copying the browser shaders.

Audio analysis supplies an onset envelope based on positive spectral flux, with
fast attack, 140 ms decay, and a 120 ms retrigger guard. Sustained tones do not
produce a continuous full-strength beat pulse. Percussion estimates drive the
individual drums; they are estimates from mixed audio, not isolated drum tracks.

Select **android-playback** on Termux and press **START AUDIO** after granting playback
capture consent in Android Bridge. The native renderer never opens a microphone.
**pipewire** captures the configured Linux input and **simulated** demonstrates
the graphics without real capture. Source selection waits for START. STOP and
leaving the screen stop capture and animation. Switching visualizer scenes or Drum Kit leaves
the audio session alive.

The browser renderer remains available via
`OPENROAD_MUSIC_VISUALIZER_RENDERER=webgl`, with its 13 existing presets and browser
microphone option. WebUi continues to use WebGL. Native GL failures display an
explicit error; select the browser override if the device cannot create a GLX context.

For PipeWire playback monitoring, set
`OPENROAD_MUSIC_VISUALIZER_PIPEWIRE_TARGET` to the appropriate monitor node.
Termux/Android defaults to Android Playback. Start **Android Bridge → Android
Playback Audio → START PLAYBACK CAPTURE**, grant audio permission, and approve
Android's capture prompt, then press **START AUDIO** in ORC.
`OPENROAD_MUSIC_VISUALIZER_SOURCE=pipewire` or `android-playback` overrides the
initial input. Capture begins only when START AUDIO is pressed. STOP and leaving
the screen release capture. Native shutdown releases the renderer; the browser
override closes Chromium and its local server.
CALIBRATE, FINISH, and CLEAR manage the shared ambient-noise profile.

In the browser override, input and preset menus render inside the browser page, avoiding native
Chromium popup windows that can fail when reparented into Termux/X11. Silence is
reported separately from a failed stream. If Android Playback connects but stays
silent, clear calibration and try a capture-permitted audio app. Inspect native
capture with `curl -s http://127.0.0.1:8768/status`; connection refused means the
bridge playback service is not running. The bridge supports one stream client,
so stop another WebUi/visualizer consumer before retrying.
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

A native GL component check creates an X11 context and the actual themed
left/right screen, renders all nine scenes, checks nonempty and distinct frames,
verifies kick/stick changes and small-window resize, and releases resources:

```bash
python -m apps.orcUi.component_test.native_music_visualizer_cli
```

This uses supplied analysis snapshots, without microphone access. Device validation:

```bash
git switch music-visualizer-modernization
git pull --ff-only
OPENROAD_MUSIC_VISUALIZER_SOURCE=android-playback ./runOrcUi
```

Start bridge capture, play a capture-permitted local MP3, press START AUDIO, and check
that tunnel pulses and individual drum activity respond. Native OpenGL uses the
existing pinned `PyOpenGL==3.1.10` and `pyopengltk==0.0.4` dependencies. Keep the
normal Termux/X11 graphics configuration; the cloud component check uses Mesa
software rendering and does not establish phone GPU compatibility.

A repeatable embedded X11/browser check is available with the optional Python
`playwright` package installed:

```bash
python -m apps.orcUi.component_test.music_visualizer_browser_cli
```

It uses a synthetic microphone and clicks all 13 page-rendered preset choices,
including fullscreen, then verifies capture cleanup on navigation. An isolated
headless X11 test host may use `--software-rendering`; normal ORC does not force
software rendering.

Hardware component checks remain separate: confirm live PipeWire monitor audio
on Linux, Android playback consent and streaming on the phone, and browser
microphone/WebGL behavior in the target browser. Passing synthetic-PCM tests does
not verify those device and permission paths.

## Architecture and resource ownership

Media composition selects presentation and owns its runtime. The native default
receives a GL backend factory from composition and immutable `VisualizerFrame`
snapshots through `MusicVisualizerPresentationIf`. The frontend chooses only how
to render those snapshots. `MusicVisualizerController` owns capture workers,
bounded latest-frame delivery, calibration, and stale completion handling. The
renderer owns its GL geometry and animation timer and releases both on close.

The browser override uses `BrowserMediaScreen` and `MusicVisualizerBrowser` for
its local host and browser lifecycle. `MusicAnalysisSession` owns audio capture
and analysis in both paths. WebUi retains the existing shared WebGL assets.
