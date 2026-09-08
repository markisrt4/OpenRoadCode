# Streaming Radio

Status: functional on the `streaming-radio` branch and in final integration testing.

## Overview

Streaming Radio adds internet station discovery and audio playback to the existing ORC Radio entry screen without replacing the SDR++ RF path. The chooser continues to offer RF Radio and Streaming Radio. The streaming browser provides Local, Regional and Favorites views plus genre, quality and band/origin filters, station artwork, selection and playback controls. Home observes the same shared streaming-radio controller and shows the active station independently of the Radio panel.

Radio Browser supplies station discovery and current metadata. mpv supplies audio playback. Internet access is required for directory requests and remote streams; the streaming path itself does not require an SDR receiver.

## Architecture and ownership

```text
apps/orcUi/application_runtime.py
  └── StreamingRadioController
        └── StreamingAudioPlayerIf
              └── MpvStreamingAudioPlayer

RadioEntryPanel
  └── PersistentStreamingRadioPanel
        ├── StreamingRadioFavorites
        │     └── PersistentCache
        └── StreamingRadioDirectoryIf
              └── RadioBrowserDirectory

Home RADIO tile
  └── same StreamingRadioController
```

The runtime owns one streaming controller and stops it during application cleanup. The Radio screen and Home summary receive that controller by injection rather than constructing their own players.

Favorites are intentionally separate from station metadata. `StreamingRadioFavorites` stores only stable Radio Browser station UUIDs. When Favorites is opened, `RadioBrowserDirectory.stations_by_ids()` resolves those UUIDs to current names, stream URLs, artwork and other metadata. This avoids persisting stale stream URLs or duplicating the directory record locally.

Favorites use the shared byte-oriented `PersistentCache`; serialization and validation remain domain policy in `StreamingRadioFavorites`. The storage root is OpenRoadCode user data rather than disposable cache data:

```text
${XDG_DATA_HOME:-~/.local/share}/openroadcode/radio/
```

The physical file name is hashed by `PersistentCache`. The logical key is versioned by the favorites store. The short-lived earlier TOML favorites format under `${XDG_CONFIG_HOME:-~/.config}/openroadcode/streaming_radio.toml` is read once for migration when no new-format favorites exist; the legacy file is not deleted.

`common/xdg_paths.py` provides shared XDG config, data, cache and state roots plus OpenRoadCode-specific helpers. It honors absolute XDG overrides and falls back to the freedesktop defaults. Existing unrelated cache users have not been migrated on this branch.

## Discovery and filtering

`StreamingRadioDirectoryIf` supports name search, station-ID resolution, regional discovery and nearby discovery. `RadioBrowserDirectory` maps Radio Browser JSON responses into immutable `StreamingRadioStation` values. Favorites are resolved through Radio Browser's UUID lookup endpoint in one batched request and then reordered to match the saved favorite order.

The integrated browser currently defaults local discovery to Detroit coordinates, an 80 km radius and Michigan. This remains a development default rather than live GPS-driven discovery.

The filter drawer provides genre/content, reported stream quality and band/origin filters. Internet-only classification is conservative and tag-based because Radio Browser does not provide an authoritative terrestrial-versus-internet-native field. FM/AM/DAB classification is best-effort metadata inference and should not be treated as authoritative RF information.

## Playback and presentation

Directory and favorite-resolution work runs off the Tk event thread. Playback requests also run on a worker thread. Station cards show selection, favorite state and playback state; the active stream receives stronger now-playing treatment and a Stop action. Home observes the same controller, so navigating away from Radio does not intentionally stop playback.

`MpvStreamingAudioPlayer` launches mpv in audio-only mode and owns the process lifecycle. `is_playing` currently means the mpv process is alive; it does not prove that buffering completed or audio is audible. More advanced buffering, reconnection, metadata and audio-focus behavior remain future work.

## Installation

From the repository root:

```bash
# Debian/Ubuntu
bash development/debian/install_streaming_radio.sh

# Termux
bash development/termux/install_streaming_radio.sh
```

Use the installer for the environment in which ORC and mpv actually run. The Termux installer includes its certificate dependency checks.

## Validation

Pull the current branch first:

```bash
git switch streaming-radio
git pull --ff-only
```

Run the focused deterministic tests:

```bash
PYTHONPATH=. python -m unittest -v \
  common.unit_test.test_xdg_paths \
  controllers.cache.unit_test.test_persistent_cache \
  controllers.radio.unit_test.test_streaming_radio \
  controllers.radio.unit_test.test_streaming_radio_controller \
  controllers.radio.unit_test.test_streaming_radio_favorites \
  hardware_io.audio.unit_test.test_mpv_streaming_audio_player \
  frontends.tk.radio.unit_test.test_streaming_radio_panel
```

Run the opt-in live Radio Browser component test:

```bash
ORC_RUN_NETWORK_COMPONENT_TESTS=1 PYTHONPATH=. \
python -m unittest -v controllers.radio.component_test.test_radio_browser_directory
```

Launch the integrated UI:

```bash
PYTHONPATH=. python -m apps.orcUi
```

For the final 1024×600 acceptance pass, verify the Radio chooser, Local and Regional station loading, filter drawer layout, play/stop, Home now-playing state, favorite add/remove, Favorites reload after restarting ORC, return navigation, shutdown while streaming, directory failure and an invalid stream. Also confirm that a persisted favorite still opens using freshly resolved directory metadata rather than data stored with the favorite.

## Remaining limitations

Streaming Radio does not yet provide GPS-driven local discovery, authoritative broadcast-band classification, integrated station search in the Tk browser, track metadata, mpv IPC, buffering/reconnect state or shared audio-focus arbitration. Those are follow-up features, not blockers for this branch.

Before merging, merge current `master` into `streaming-radio`, resolve only genuine conflicts, rerun the focused and live tests, and repeat the 1024×600 smoke test. Keep broader XDG migration and unrelated runtime refactors out of this branch.
