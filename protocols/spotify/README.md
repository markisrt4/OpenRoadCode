# Spotify Protocol

The `spotify` protocol component provides Spotify-specific authentication and communication with the Spotify Web API.

It builds upon the generic OAuth protocol component for OAuth 2.0 and PKCE authentication.

## Components

The Spotify protocol includes:

- Spotify configuration
- Spotify OAuth authentication
- Spotify OAuth token storage
- Spotify Web API client
- Spotify installation script

## Directory Layout

```text
spotify/
├── __init__.py
├── install_spotify.sh
├── spotify_auth.py
├── spotify_config.py
├── spotify_token_store.py
├── spotify_web_api_client.py
├── README.md
└── component_test/
    ├── __init__.py
    └── spotify_auth_cli.py
```

## Installation

Before using the Spotify protocol you must create a Spotify Developer application.

1. Visit the Spotify Developer Dashboard.
2. Create an application.
3. Add the following Redirect URI:

```text
http://127.0.0.1:8888/callback
```

4. Copy the application's Client ID.

Run the installation script:

```bash
./install_spotify.sh
```

The installer will:

- Prompt for the Spotify Client ID
- Store configuration in the shared OpenRoadCode secrets file
- Launch the Spotify authorization flow
- Store OAuth tokens locally

Configuration is stored in:

```text
~/.config/openroadcode/secrets.env
```

OAuth tokens are stored in:

```text
~/.config/spotify/tokens.json
```

Neither file should be committed to source control. Process environment
variables override values from the secrets file when needed for testing. The
legacy `/etc/openroadcode/secrets.env` remains a lower-priority compatibility
fallback.

## Authentication

`SpotifyAuth` performs Spotify authorization using OAuth 2.0 with PKCE.

It uses the generic OAuth protocol component for:

- Authorization URL generation
- PKCE
- Redirect handling
- Token exchange
- Token refresh

Stored access tokens are reused whenever possible.

Expired access tokens are automatically refreshed.

## Spotify Web API Client

`SpotifyWebApiClient` communicates with the Spotify Web API.

It supports:

- Authenticated HTTP requests
- JSON responses
- Automatic OAuth access token retrieval
- HTTP error handling

The client provides access to Spotify resources including:

- Current playback state
- Playback devices
- Album information
- Artist information
- Album artwork URLs
- Volume
- Track position
- Playback control
- Playback of a specific recognized track URI
- Track metadata lookup for song-recognition artwork enrichment

The Web API client returns Spotify data only.

It does not download album artwork or perform image caching.

## Component Test

A CLI component test is provided.

Run from the project root:

```bash
python3 -m protocols.spotify.component_test.spotify_auth_cli
```

Force a new authorization:

```bash
python3 -m protocols.spotify.component_test.spotify_auth_cli \
    --clear-tokens
```

## Design

The Spotify protocol is responsible only for Spotify-specific communication.

Responsibilities include:

- OAuth authentication
- Web API communication
- Spotify request and response handling

Playback logic, media state management, album artwork downloading, image caching, and user interface behavior belong in higher-level controller or application components.

Generic OAuth functionality is implemented by the `protocols.oauth` package.
