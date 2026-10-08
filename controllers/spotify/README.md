# Spotify Controllers

The Spotify controller package is the application-facing boundary between OpenRoadCode user interfaces and Spotify. UI code should use these controllers or the shared `SpotifyStateService`; it should not issue Spotify HTTP requests directly.

## Responsibilities

- `SpotifyControllerIf` defines playback, Connect transfer, saved-library, recent-history, and direct-track playback operations.
- `SpotifyWebApiController` implements that contract through `protocols/spotify`.
- `SpotifyMediaPresenter` converts Spotify playback state into the toolkit-neutral `ui.media.MediaState` model.
- `SpotifyStateService` serializes backend access, caches playback/library state, queues semantic media requests, and keeps Spotify API work off UI threads. The concrete backend is injected by application composition.
- `SpotifyLocalPlayer` owns the reusable local Spotify Connect/Web Playback SDK lifecycle and playback-destination state. Host-specific browser and Web Player adapters are injected by application composition.
- `MockSpotifyController`, `SpotifyControllerStub`, and `UnconfiguredController` preserve useful development and configuration seams.
- `SpotifyLibraryTrack` is the immutable application-facing model for saved and recently played tracks.

The controller package deliberately does not own OAuth setup, application composition, Tk widgets, or host-specific screen layout. OAuth and HTTP transport belong in `protocols/spotify`; presentation belongs to `ui` and `frontends`. ORC-specific composition remains responsible for selecting browser candidates, data paths, window geometry, and the concrete Web Player host adapter used by `SpotifyLocalPlayer`.

## OAuth permissions

The current feature set requests playback-state/control, Web Playback SDK, private-profile, saved-library, recently-played, and private-playlist scopes. Scope declarations live in `protocols/spotify/spotify_config.py`. Existing cached OAuth tokens must be reauthorized after new scopes are added.

Spotify uses PKCE in OpenRoadCode. No Spotify client secret belongs in this repository.

## Playback modes

ORC supports two destination concepts:

- **REMOTE** controls the active external Spotify Connect device.
- **PLAYER** registers OpenRoadCode itself as a Connect device using the Spotify Web Playback SDK, then transfers playback to it.

PLAYER mode is currently verified with Google Chrome stable on Debian/Ubuntu AMD64. Termux remains REMOTE-only because its Chromium environment does not provide the media/EME support required by the SDK.

## Structured media logging

ORCui configures the shared [ORC logger](../../common/logging/README.md). Media
records use the same JSON Lines store, rotation, severity controls, and live viewer:

```bash
./runOrcUi --follow-logs --log-component media
```

| Component | Events |
| --- | --- |
| `media.lifecycle` | Application media services start/stop and failures |
| `media.library` | Spotify library/history/playlist loads, item counts, and failures |
| `media.spotify` | Queued/completed/failed commands, rate limiting, worker lifecycle, observed availability/playback/track changes |
| `media.spotify.api` / `media.spotify.presenter` | State-read failure and recovery transitions, including errors retained as UI fallback state |
| `media.spotify.player` | Local player requests, registration, startup/cleanup failures, and resource release |
| `media.spotify.sdk` | SDK host lifecycle, ready/error transitions, and approved error categories |
| `media.browser` | Managed browser show/close completion and failures |
| `media.video` | Music-video lookup, launch, stop, return to Spotify, and failures |
| `media.audio` | System audio availability/recovery and volume/mute failures |

Library loads here are Spotify API queries, not local filesystem scans. Cache
hits and unchanged state stay quiet at INFO. Position polling and volume/seek
commands stay at DEBUG, including system volume/mute command completion.
Audio availability changes are detected by the existing refresh calls; this
does not enumerate or select output devices.

Each queued Spotify action keeps its operation ID when the worker executes it.
Local-player activation carries its ID into the startup thread, SDK callback
threads, and queued transfer. Library/video/browser actions use local operation
IDs without changing Spotify wire contracts. SDK error categories are restricted
to known values; SDK messages and device IDs are not printed or logged.

`command.completed` means the backend call returned successfully. Playback state
changes are logged separately when observed. `player.registered` means the SDK
registered a device and transfer was queued, not that playback was confirmed.
Browser show/close events reflect the runtime manager's policy, which can reuse
or hide a process. Browser/video launch does not prove audible playback, successful
decoding, or DRM support.

Structured media records exclude track titles/artists/albums, playlist and device
identifiers, URLs, queries, file paths, OAuth credentials, API bodies, playback
positions, and raw exception messages, even at DEBUG. Existing UI error messages
and separate browser diagnostic files retain their existing behavior; browser
output is not copied into the structured store.

For standalone controller tools, configure logging at the process entry point.
No additional install dependencies are needed. The logging quality gate tests
schema, correlation across real worker threads, failures, privacy exclusions,
cache retention, quiet polling, rate backoff, and resource cleanup without Spotify,
a browser, audio hardware, or a display. Real provider/device playback remains
an installed-system smoke test.

## Tests

Run the focused controller tests from the repository root:

```bash
python3 -m unittest discover -s controllers/spotify/unit_test -p 'test_*.py'
```
