# ORC Media Integration

The `orcUi` Media surface integrates Spotify, YouTube, and Netflix while keeping service protocols, browser lifecycle, X11 mechanics, and Tk presentation separated.

## Spotify

`SpotifyStateService` owns the shared background controller used by Home and Media. It serializes Web API access, caches now-playing state, and keeps network/control operations off the Tk event thread.

The Media landing card offers two entry paths:

- **REMOTE** opens Spotify controls without changing the active external Spotify Connect device.
- **PLAY HERE** starts the ORC local Web Playback SDK device, transfers playback to it, and opens the same Spotify UI.

The Spotify screen also exposes **Liked Songs** and **Recently Played**. Collection retrieval runs on a worker thread and selecting a returned track queues playback through the shared Spotify service.

Because library/history permissions were added after the original playback integration, existing users must reauthorize Spotify once so the cached token includes the new scopes.

## Local Spotify playback

`SpotifyLocalPlayer` owns the local SDK host and browser backend. The browser is an audio implementation detail and is hidden after the SDK registers the `OpenRoadCode` Connect device. PLAYER mode is currently verified with Google Chrome stable on Debian/Ubuntu AMD64. Spotify Premium is required by the Web Playback SDK.

Termux remains REMOTE-only because its current Chromium environment does not provide the required Web Playback/EME capability.

## YouTube and Netflix

`YouTubePlayer` and `NetflixPlayer` own semantic browser-backed playback operations. `BrowserKioskLauncher` owns process lifecycle, and `X11WindowEmbedder` owns native reparenting into the ORC media surface.

Both services use persistent dedicated browser profiles so login state can survive application restarts. Netflix protected playback additionally requires browser Widevine/DRM support; Termux Chromium currently does not provide it.

## Configuration

Spotify secrets are installed separately from browser/media runtime dependencies:

```bash
./development/debian/install_secrets.sh
./development/debian/setup_media.sh
```

OAuth/token details live in `protocols/spotify/README.md`; application-facing Spotify behavior lives in `controllers/spotify/README.md`; browser-backed video behavior lives in `controllers/video/README.md`.
