# Music visualizer

The refreshed visualizer uses shared PCM capture and FFT analysis for the native
ORC UI and WebUi. Frontends render analysis state; Android permissions and audio
capture stay in the platform backend.

## Native ORC UI

Start the normal desktop or Termux:X11 session, run `./runOrcUi`, then open
**Media → Music Visualizer**. The source selector provides:

- **simulated**: animated demo frames without audio hardware or capture.
- **pipewire**: mono audio from `pw-record` on Linux. Install the host's PipeWire
  tools (`pipewire-bin` on Debian/Ubuntu) and run in the user's audio session.
  To visualize playback instead of a microphone, select the appropriate monitor
  node with `OPENROAD_MUSIC_VISUALIZER_PIPEWIRE_TARGET`.
- **android-playback**: the Android bridge's localhost PCM stream at
  `http://127.0.0.1:8768/stream`. Start playback capture and grant the Android
  consent prompt in the bridge app first. Capture-restricted applications may
  not provide audio. ORC consumes the stream; it does not request MediaProjection.

Selecting a source starts it. **STOP** releases capture; **START** restarts it.
Leaving the screen releases capture. The eight native modes are Spectrum,
Orbiting Planets, Electric Freeway, Explosion Field, Star Dance, Electric Rings,
Neon Ribbon, and Kaleidoscope. Rendering and widget updates stay on the Tk thread;
capture and analysis run in the background, retaining only the latest frame.

The default source is simulation. Set `OPENROAD_MUSIC_VISUALIZER_SOURCE` to
`simulated`, `pipewire`, or `android-playback` to choose the initial source.
`OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE` defaults to 2048 samples and must be at
least 2048. Capture errors appear on the screen; they do not silently select a
different source.

To remove ambient noise, start a real input, press **CALIBRATE** while the input
is quiet, then **FINISH**. **CLEAR** discards the noise profile. Changing source
creates a new analysis session; calibration does not carry between sources.

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
