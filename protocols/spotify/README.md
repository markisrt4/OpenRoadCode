# Spotify Protocol Integration

`protocols/spotify` owns Spotify-specific OAuth and Web API transport. Application code should normally depend on `controllers/spotify` rather than this package directly.

## Configuration

OpenRoadCode uses Spotify OAuth Authorization Code with PKCE. The public Client
ID configured through the desktop UI is stored in the user's XDG configuration
at `~/.config/openroadcode/spotify/application.json`. Process environment takes
precedence over that user setting, which in turn takes precedence over the
administrator-managed system secrets file.

Required value:

```text
SPOTIFY_CLIENT_ID=<Spotify application client id>
```

Optional redirect override:

```text
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

No client secret is required or expected. The optional redirect override remains
administrator-controlled through the environment or system secrets file.
Credentials and OAuth tokens must never be committed.

The configuration dialog expects the 32-character Client ID shown by the
Spotify Developer Dashboard, not an access token, API token, or client secret.
Changing the Client ID clears cached OAuth tokens because they belong to the
previous Spotify application.

The canonical OAuth scopes are declared in `spotify_config.py`. They currently cover playback state/control, Web Playback SDK streaming, profile access, saved tracks, recently played tracks, and private playlists. When scopes change, an existing token cache may not contain the new permissions. Re-authorize the cached Spotify token before testing features that depend on newly added scopes.

## Components

- `SpotifyConfig` translates runtime settings into the generic OAuth configuration.
- `SpotifyAuth` owns Spotify authorization and token refresh behavior.
- `SpotifyTokenStore` persists OAuth tokens outside the repository.
- `SpotifyWebApiClient` performs authenticated requests against the Spotify Web API.

HTTP paths, JSON parsing into application models, and semantic operations such as saved-library/history retrieval belong in `controllers/spotify`, not in the transport layer.

## Token storage

OAuth tokens are stored by default at:

```text
~/.config/spotify/tokens.json
```

Stored access tokens are reused and refreshed when possible. To force authorization after a scope change:

```bash
python3 -m protocols.spotify.component_test.spotify_auth_cli --clear-tokens
```

Playback controllers use token access non-interactively: a missing or
non-refreshable token is reported as disconnected and never opens a browser from
a background refresh worker. Desktop authorization begins only from the
explicit Connect action. The desktop composition hands the authorization URL to
the system browser with in-process GUI toolkit plugin overrides removed.

## Platform setup

Debian/Ubuntu credentials can be configured with:

```bash
./development/debian/install_secrets.sh
```

Termux uses the corresponding secrets setup under `development/termux`. Spotify REMOTE mode does not require a local Web Playback browser. PLAYER mode additionally requires a compatible browser; the verified Linux path is Google Chrome stable.

## Component test

From the repository root:

```bash
python3 -m protocols.spotify.component_test.spotify_auth_cli
```

## Boundary

This package is intentionally transport-focused. Playback policy, Connect destination selection, library presentation, artwork caching, and UI behavior belong in controllers/services/applications. Generic OAuth mechanics remain in `protocols.oauth`.
