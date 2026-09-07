# Streaming Radio

Status: experimental, functional on the `streaming-radio` branch. This document describes the implemented integration as of September 7, 2026, not a finished release.

## Overview

Streaming Radio adds internet station discovery and audio playback to the existing ORC Radio entry screen. It does not replace SDR++ or the RF radio path. The Radio chooser retains its RF Radio and Streaming Radio cards. The streaming browser provides Local, Regional, Favorites and Internet Only views, station artwork, selection and playback controls. The active station receives prominent now-playing treatment, and Home has a separate radio-owned summary.

The feature uses Radio Browser for discovery and mpv for audio. It requires an internet connection for directory requests and remote streams. It does not require an SDR receiver, and audio-only mpv does not require X11. The integrated Tk application still requires its normal graphical environment.

## Architecture and ownership

```text
apps/orcUi/main.py (composition)
  ├── OrcUiApplicationRuntime
  │     └── StreamingRadioController
  │           └── StreamingAudioPlayerIf
  │                 └── MpvStreamingAudioPlayer → mpv process
  ├── RadioScreen → RadioEntryPanel → StreamingRadioPanel
  │                                      └── StreamingRadioDirectoryIf
  │                                            └── RadioBrowserDirectory → HTTPS
  └── OrcUiApp → Home RADIO tile → StreamingRadioNowPlaying
                                      └── same StreamingRadioController
```

`application_runtime.py` constructs one streaming controller and owns its shutdown. `main.py` injects that controller into the Radio screen and Home summary. Home does not own a second player or inspect the radio panel's widgets. The shell exposes `set_home_radio_factory`, parallel to its existing media factory, so radio presentation remains independently owned.

The important source files are:

| Area | File | Responsibility |
| --- | --- | --- |
| Station model | `controllers/radio/streaming_radio_types.py` | Immutable station identity, URLs and metadata |
| Directory contract | `controllers/radio/streaming_radio_directory_if.py` | Search, regional and nearby discovery |
| Directory adapter | `controllers/radio/adapters/radio_browser_directory.py` | Radio Browser HTTP requests and response mapping |
| Playback controller | `controllers/radio/streaming_radio_controller.py` | Current station and play/stop coordination |
| Audio contract | `controllers/audio/streaming_audio_player_if.py` | Player-independent playback operations |
| Audio adapter | `hardware_io/audio/mpv_streaming_audio_player.py` | External mpv process lifecycle |
| Browser | `frontends/tk/radio/streaming_radio_panel.py` | Station browsing, artwork and touch controls |
| Home summary | `apps/orcUi/streaming_radio_now_playing.py` | Current station presentation and Radio navigation |
| Composition | `apps/orcUi/application_runtime.py`, `apps/orcUi/main.py` | Shared service construction, injection and cleanup |

The station model contains `station_id`, `name`, `stream_url`, optional homepage/artwork URLs, state, country code, codec, bitrate, tags and optional coordinates. The directory interface returns immutable tuples of stations. Its methods are `search(query, limit=20)`, `stations_by_region(state, country_code='US', limit=50)` and `stations_near(latitude, longitude, radius_km, state, country_code='US', limit=50)`.

The controller exposes `current_station`, `is_playing`, `play(station)` and `stop()`. It delegates audio operations to the injected player. The mpv adapter launches audio-only playback with `--no-video --really-quiet -- URL`, redirects standard streams to DEVNULL, and terminates the owned process on stop, escalating to kill after its configured timeout. The runtime also stops streaming playback during application cleanup.

## Discovery and classification

The current adapter uses the Radio Browser JSON API, with `https://de1.api.radio-browser.info/json` as its default endpoint. Requests use a bounded timeout and an ORC User-Agent. Search and regional discovery use station metadata supplied by the directory. Nearby discovery retrieves statewide candidates, calculates Haversine distances for entries with coordinates, sorts nearby results and retains entries without coordinates as regional fallback candidates.

The integrated browser currently defaults to Detroit coordinates (42.3314, -83.0458), an 80 km radius and Michigan. This is a development default, not live GPS-based discovery. The CLI permits overriding the coordinates, radius, state and country. The UI currently requests up to 50 local or 100 regional stations.

Internet Only uses conservative explicit-tag classification. Tags such as `internet`, `internet only`, `online only`, `web radio` and `webradio` identify candidates. Radio Browser metadata does not reliably distinguish internet-native stations from terrestrial stations that also stream. Consequently, the filter is not an authoritative classification, and untagged internet-native stations may be excluded. The normal view also excludes explicitly internet-only entries. A future directory policy should make this distinction more reliable without inventing station metadata.

Favorites are currently session-only station IDs. They are not persisted to disk or synchronized across devices. The Favorites view filters the stations currently loaded in the browser, so it is not yet a complete independent favorites directory. Search is available through the CLI; the integrated browser currently exposes Local, Regional, Favorites and Internet Only rather than a search field.

## User interface and playback state

The browser loads directory data on a worker thread and returns results to Tk for rendering. Artwork is fetched through a bounded thread pool, limited to 2 MiB per response, converted to RGB and fitted to 64×64 pixels. Images are retained in a panel-local cache. Directory and artwork failures must not prevent the rest of the UI from operating.

Station cards provide artwork, name, metadata, favorite selection and Play/Stop. The active station uses a stronger green border, a NOW PLAYING banner, larger title and prominent Stop control. A separate footer reports selection, connection, playback or failure status. Playback operations run on a worker thread rather than blocking the Tk event loop.

The Home RADIO tile uses the same controller and displays the current station, available metadata and an Open Radio action. Its periodic refresh observes the controller's state. The Home MEDIA tile remains independently owned by the media/Spotify integration. Navigating away from Radio does not intentionally stop the stream; application shutdown does.

`is_playing` currently means that the owned mpv process is still running. It is not proof that audio is audible, buffering has completed, or a remote stream is healthy. The controller stores the last successfully requested station and clears it on stop. There is no dedicated buffering/error state machine, mpv IPC, stream metadata reader or shared audio-focus arbitration yet.

## Installation

From the repository root, install the target-specific dependencies:

```bash
# Debian/Ubuntu
bash development/debian/install_streaming_radio.sh

# Termux
bash development/termux/install_streaming_radio.sh
```

The installers provide mpv and certificate dependencies. The Termux installer explicitly installs `ca-certificates` and checks its expected certificate bundle. A working network connection and valid TLS certificates are required for HTTPS directory requests. The integrated UI also needs its normal Python/Tk/Pillow dependencies and graphical environment.

Do not run the Debian installer inside Termux's native package environment or assume the Termux installer configures a Debian proot. Install in the environment where the Python application and mpv backend will execute. Audio output follows mpv's available platform audio configuration; no dedicated ORC output-device selector is implemented here.

## Running and validating

Use the repository root and the existing branch. Do not create another branch for this feature.

```bash
git switch streaming-radio
git pull --ff-only

PYTHONPATH=. python -m unittest -v \
  controllers.radio.unit_test.test_streaming_radio \
  controllers.radio.unit_test.test_streaming_radio_controller \
  hardware_io.audio.unit_test.test_mpv_streaming_audio_player \
  frontends.tk.radio.unit_test.test_streaming_radio_panel
```

The network component test is opt-in because it contacts an external directory:

```bash
ORC_RUN_NETWORK_COMPONENT_TESTS=1 PYTHONPATH=. \
python -m unittest -v controllers.radio.component_test.test_radio_browser_directory
```

The CLI provides a useful independent smoke test before debugging Tk:

```bash
PYTHONPATH=. python -m controllers.radio.component_test.streaming_radio_cli
PYTHONPATH=. python -m controllers.radio.component_test.streaming_radio_cli --regional --state Michigan --limit 50
PYTHONPATH=. python -m controllers.radio.component_test.streaming_radio_cli --search WDET
PYTHONPATH=. python -m controllers.radio.component_test.streaming_radio_cli --latitude 42.3314 --longitude -83.0458 --radius-km 120
```

Select a station number, listen, and press Enter to stop. The CLI constructs its own controller and mpv player, so it should not be run concurrently with the integrated UI when testing exclusive audio ownership.

Launch the integrated application in its configured graphical session:

```bash
PYTHONPATH=. python -m apps.orcUi
```

For a manual acceptance pass, open Radio → Streaming Radio, load Local and Regional stations, select and play a station, verify the active card and Stop control, navigate to Home, confirm the RADIO tile shows the same station, then return to Radio. Stop playback and confirm Home returns to its idle presentation. Also check directory failure, an invalid stream, repeated play/stop, and navigation away while playing. These are acceptance checks, not claims that every case has passed on every target.

The earlier deterministic and live directory/controller tests were reported passing during branch development. The latest Home and active-card changes still require a fresh local regression and visual pass. No full-repository or cross-platform test result is claimed here.

## Troubleshooting

If imports fail with `No module named controllers`, run from the repository root and set `PYTHONPATH=.`. If directory loading fails, check network access, TLS certificates and the Radio Browser service before changing UI code. If stations appear but audio is silent, verify `mpv --version`, test a known stream with mpv directly, and inspect the host audio output and volume. The current backend suppresses mpv output, so it does not provide detailed stream diagnostics in the UI.

If Home does not reflect playback, confirm that the composition root injects the same controller into both the browser and Home widget. Do not create a second player to fix a presentation problem. If the active station disappears from the browser after changing filters, remember that the directory list and current playback are separate; the Home summary should still report the active stream.

## Known limitations and next steps

This branch does not yet provide persistent favorites, reliable internet-native classification, GPS-driven local discovery, a complete favorites catalog, integrated station search, shared artwork caching, track metadata, buffering/reconnection state, audio-focus arbitration or a full player-state subscription contract. The current Home widget polls controller state and the browser maintains its own selection and busy state. A future shared presentation/state service can consolidate these without moving process ownership into Tk or the shell.

Before merging, complete the focused regression tests and 1024×600 visual acceptance pass, review the Home integration and shutdown behavior, and update the root README to remove its obsolete Coming Soon description. Keep unrelated navigation, media and runtime refactors outside this branch.
