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

## Tests

Run the focused controller tests from the repository root:

```bash
python3 -m unittest discover -s controllers/spotify/unit_test -p 'test_*.py'
```
