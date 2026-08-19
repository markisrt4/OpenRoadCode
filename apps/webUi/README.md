# OpenRoadCode WebUi

`apps/webUi` is the standalone browser frontend for OpenRoadCode.

The application bootstrap lives under `apps/webUi`, while reusable browser rendering and browser-only capabilities live under `frontends/web`.

## Run

From the repository root:

```bash
python3 -m apps.webUi.main
```

Then open:

```text
http://127.0.0.1:5000/
```

This works well for local testing under Termux on Android.

## Architecture

WebUi is intentionally independent from CarUi.

- `apps/webUi` owns application composition and Flask runtime state.
- `frontends/web` owns browser rendering, JavaScript, and browser-native capabilities.
- `controllers` own application/domain behavior and normalized state.
- Browser sensor acquisition remains in `frontends/web/sensors`, then posts through WebUi into controller-side navigation adapters.
- Controllers do not own Flask routes or HTTP servers.

Some WebUi panels are experimental or browser-native equivalents rather than feature-for-feature ports of CarUi.

## Phone sensors

The Off-Road panel can use browser geolocation and device-orientation APIs.

Open:

```text
Gauges -> Off-Road
```

and press `START SENSORS`.

The browser posts position and orientation samples into WebUi, where they are normalized into the same navigation state contracts used elsewhere in OpenRoadCode.

## Spotify

Spotify uses the shared OpenRoadCode Spotify controller, media presenter, OAuth implementation, and token store.

Set the Spotify client ID before launching WebUi:

```bash
export SPOTIFY_CLIENT_ID="..."
export SPOTIFY_REDIRECT_URI="http://127.0.0.1:5000/api/media/spotify/auth/callback"
```

Register this exact redirect URI in the Spotify Developer Dashboard:

```text
http://127.0.0.1:5000/api/media/spotify/auth/callback
```

Start authorization with:

```text
http://127.0.0.1:5000/api/media/spotify/auth/start
```

Successful authorization writes the normal token store at:

```text
~/.config/spotify/tokens.json
```

The Web Spotify panel supports playback state, artwork, track metadata, seeking, synchronized lyrics, playback controls, and browser-native music-video lookup. Device volume control is disabled when the active Spotify device reports that remote volume is unsupported.

## Browser media

YouTube and Netflix panels use browser-native launch/search behavior. They intentionally do not introduce controller abstractions while their only responsibility is opening external browser content.

## Health endpoint

```text
GET /healthz
```

returns a small JSON response indicating that the Web frontend is running.
