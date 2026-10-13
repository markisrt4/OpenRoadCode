# Music visualizer

The refreshed visualizer uses shared PCM capture and FFT analysis for the native
ORC UI and WebUi. Frontends render analysis state; Android permissions and audio
capture stay in the platform backend.

## ORC UI

Run `./runOrcUi`, then open **Media → Music Visualizer**. ORC now defaults to
native OpenGL in its Tk Media screen, using the existing GLX backend shared with
the ECU renderer (including Termux/X11 compatibility). No browser process or local
HTTP server is created for this renderer.

The native icon grid offers ten distinct scenes: Frequency Tunnel, Spectrum Field,
Orbiting Planets, Electric Freeway, Explosion Field, Star Dance, Electric Rings,
Neon Ribbon, Kaleidoscope, and Frequency Analyzer. Frequency Tunnel sends spectrum-shaped rings
through a 3D tunnel, expanding and brightening on musical onsets. **Drum Kit**
switches the same GL surface to lacquered, layered drum shells, chrome hoops and
tension rods, subtly moving drumheads, tripod stands, bass pedals, and curved
cymbals with machined grooves and restrained wobble. Drum sticks are removed.
The camera starts much closer;
DRUM ZOOM adjusts the framing while preserving the kit on narrow surfaces.
Single/double kick layouts share the same capture and calibration. The **Beat response** slider changes visual pulse strength.
The prominent **VISUALS / DRUMS** buttons select the view and highlight the active
choice. All controls live in a compact ORC-themed rail on the left; the GL surface
fills the right side. **AUDIO** contains source and calibration controls; **SCENE**
contains the selected view's options. START/STOP remain available in both tabs.
No scrolling is required. CAL collects paused ambient sound, SAVE applies it, and
CLEAR removes calibration.
Selecting a scene immediately shows it without restarting capture. These native
scenes use their own GL geometry rather than copying the browser shaders.

Audio analysis supplies an onset envelope based on positive spectral flux, with
fast attack, 140 ms decay, and a 120 ms retrigger guard. Sustained tones do not
produce a continuous full-strength beat pulse. Percussion estimates drive the
individual drums; they are estimates from mixed audio, not isolated drum tracks.
Drum response is independent of visualizer beat gain. Its lower default (0.6)
and nonlinear gate suppress sustained activity below 0.22 and soften intermediate
values; distinct hits still produce a clear response. **DRUM RESPONSE** adjusts
that gain without changing capture, calibration, or visualizer pulse strength.
Detailed cymbal meshes are cached in GL display lists and released on close.

Select **android-playback** on Termux and press **START AUDIO** after granting playback
capture consent in Android Bridge. The native renderer never opens a microphone.
**pipewire** captures the configured Linux input and **simulated** demonstrates
the graphics without real capture. Source selection waits for START. STOP stops capture and animation. Navigating between the full visualizer and
an enabled HOME preview preserves capture; leaving both releases it after a short
navigation handoff. Switching visualizer scenes or Drum Kit leaves
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
initial input. Capture begins only when START AUDIO is pressed. STOP releases capture; leaving all visualizer presentations also releases it. Native shutdown releases the renderer; the browser
override closes Chromium and its local server.
CAL, SAVE, and CLEAR manage the shared ambient-noise profile.

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

## HOME Media card

The existing Media card keeps its placement beside Radio, below the map. Choose
**VISUALIZER** to mount a compact native preview or **PLAYING** for the existing
now-playing presentation. Tap the preview or OPEN to open the full visualizer.
START explicitly connects the last selected audio source; mounting a preview
never requests microphone access or starts capture automatically.

HOME and the full view share one controller, capture connection, calibration,
and preset/view preferences. The card remembers the selected presentation while
navigating. Each mounted visualizer retains a presentation lease; a short 250 ms
handoff allows navigation without disconnecting the bridge's sole stream client.
Switching to Playing or leaving both views stops capture and rendering. Shutdown
cancels handoff timers and closes the shared controller.

A native handoff component check uses synthetic PCM, with no microphone:

```bash
python -m apps.orcUi.component_test.home_music_visualizer_cli
```

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
left/right screen, renders all ten scenes, checks nonempty and distinct frames,
verifies kick changes and a 250-pixel-high control layout, and releases resources:

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


### Customizable frequency analyzer and drum controls

The native **Frequency Analyzer** defaults to smooth ORC-blue bars on a fixed
31.25 Hz–16 kHz logarithmic axis. Frequency labels and bass (below 250 Hz), mid
(250 Hz–4 kHz), and treble ranges sit below the plot. Grid lines represent
−60, −40, −20, and 0 dBFS from bottom to top. Bars report the strongest
Hann-window FFT bin in each displayed band, without adaptive normalization or
noise calibration. Bands with no FFT bins stay empty; at 48 kHz with 2048 samples,
bin spacing is 23.4375 Hz. This is a frequency/amplitude analyzer, not a calibrated
sound-pressure meter. Off-bin tones can show Hann-window scalloping loss.

Smaller kick drums and a separate snare leave clear horizontal gaps even with
double kicks. New percussion onsets trigger short illuminated heads and a downward
cymbal tilt that settles quickly; steady activity does not sustain the flash.
The existing drum-response threshold still suppresses weak background activity.
All response and zoom sliders retain drag adjustment and add large **− / +**
buttons in 0.1 steps, clamped to their limits, without restarting capture.


The SCENE page uses a five-column icon grid for visualizer selection. Each tile
has a vector preview of its effect; the selected tile is highlighted and its full
name appears below the grid. Tiles support touch, mouse, and keyboard activation.
Selection preserves the current audio session and is shared with the HOME preview.


Open **STYLE** to select the Frequency Analyzer and customize it. This keeps the
current capture running. Four compact appearance pages fit the 250-pixel viewport:

- **LOOK:** smooth/segmented bars, peak markers, and bar width (20–100% of each frequency slot).
  Larger width reduces spacing; the bounds prevent adjacent frequency bars overlapping.
- **COLOR:** ORC blue, Retro green-to-red, Monochrome, Fire, or a custom gradient.
  BASE COLOR and TIP COLOR open native color pickers. Cancel leaves settings intact.
  For the original boombox look, choose Retro colors and enable segmented bars.
- **MOVE:** rise time (0–0.3 seconds; zero gives immediate attack) and decay time
  (0.1–1.5 seconds). These are display envelopes, not analysis normalization.
  Peak markers hold for half a second before falling. Stale capture decays to zero.
- **TEXT:** independently show frequency labels and bass/mid/treble guides.

RESET APPEARANCE restores modern defaults. Settings are shared between the full
screen and HOME preview for the current ORC session; they are not saved to disk.
The fixed 31.25 Hz–16 kHz frequency axis and −60–0 dBFS scale remain unchanged.
All appearance sliders include larger minus/plus buttons with clamped limits.


Smooth bars use GPU-interpolated gradients (one rectangle per bar, or two for
Retro's yellow midpoint). All bars are batched together, as are peak markers.
Segmented bars share the same response/decay envelopes; switching style does not
add smoothing. This avoids the previous 32 strips per smooth bar, which could
make smooth mode slower than segmented mode on Termux/X11.


Routine GLX context initialization messages from pyopengltk are logged at DEBUG
rather than printed each time a native view opens. Unexpected backend output is
logged as a warning; exceptions and driver stderr remain visible. To inspect the
routine details, launch `./runOrcUi --log-level DEBUG`.


The frequency axis now uses two staggered rows of labels: octave landmarks plus
third-octave frequencies such as 40, 50, 80, 100, 160, 200, 315 and 630 Hz,
1.25, 1.6, 2.5, 3.15, 5, 6.3, 10 and 12.5 kHz. Labels are added only where they
fit without overlapping; frequency positions remain logarithmically accurate.

Taller windows (at least 430 pixels high and 500 pixels wide) expand the left rail
to 260–300 pixels with larger fonts, 40-pixel scene icons, taller buttons and wider
slider handles. Shorter windows retain the compact 180-pixel rail. Resizing and
switching control pages preserve capture and the existing OpenGL context.

Explosion Field now renders three warm, expanding spark bursts with short streaks,
falling sparks and onset shockwaves. Star Dance uses filled, rotating five-point
stars drifting over a cool starfield, with spectrum/beat-driven scale. Kaleidoscope
fills the viewport with 16 mirrored wedges, six radial layers and 864 colored
triangles; rotation, facet shapes and brightness respond to time, spectrum and beats.
These scenes batch geometry to keep the richer content practical on native GL.
