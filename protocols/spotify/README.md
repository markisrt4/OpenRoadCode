# Spotify Protocol Integration

`protocols/spotify` owns Spotify-specific OAuth and Web API transport. Application code should normally depend on `controllers/spotify` rather than this package directly.

## Configuration

OpenRoadCode uses Spotify OAuth Authorization Code with PKCE. Runtime configuration is read through the project secret-manager abstraction.

Required value:

```text
SPOTIFY_CLIENT_ID=<Spotify application client id>
```

Optional redirect override:

```text
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

No client secret is required or expected. Credentials and OAuth tokens must never be committed.

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
