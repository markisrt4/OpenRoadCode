# Spotify Controllers

The Spotify controller package is the application-facing boundary between OpenRoadCode user interfaces and Spotify. UI code should use these controllers or an owning service such as `apps/orcUi/spotify_state_service.py`; it should not issue Spotify HTTP requests directly.

## Responsibilities

- `SpotifyControllerIf` defines playback, Connect transfer, saved-library, recent-history, and direct-track playback operations.
- `SpotifyWebApiController` implements that contract through `protocols/spotify`.
- `SpotifyMediaPresenter` converts Spotify playback state into the toolkit-neutral `ui.media.MediaState` model.
- `MockSpotifyController`, `SpotifyControllerStub`, and `UnconfiguredController` preserve useful development and configuration seams.
- `SpotifyLibraryTrack` is the immutable application-facing model for saved and recently played tracks.

The controller deliberately does not own OAuth, token persistence, browser lifecycle, Tk widgets, or Web Playback SDK hosting. OAuth and HTTP transport belong in `protocols/spotify`; local playback-device lifecycle belongs to `apps/orcUi/spotify_local_player.py`; presentation belongs to `ui`, `frontends`, and `apps`.

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
python3 -m unittest controllers.spotify.unit_test.test_spotify_web_api_controller
```
