# ORC Media Integration

The `orcUi` Media surface integrates Spotify, YouTube, and Netflix while keeping service protocols, browser lifecycle, X11 mechanics, and Tk presentation separated. See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete application composition and ownership model.

## Composition and ownership

`composition/media.py` constructs the media presentation graph using the shared `OrcUiApplicationRuntime`. It wires the MEDIA hub, Spotify screen, browser-backed screens, HOME now-playing widget, image cache, lyrics client, and music-video controller. `MediaComposition.close()` releases its owned music-video resource. The application runtime owns shared media services and managed application launchers. HOME and MEDIA must not create separate Spotify state services.

The media navigation bar provides navigation between the hub, Spotify, YouTube, Netflix, and HOME. Individual provider screens do not need duplicate provider-selection buttons.

## Spotify

`SpotifyStateService` owns the shared background controller used by Home and Media. It serializes Web API access, caches now-playing state, and keeps network/control operations off the Tk event thread.

The Media landing card offers two entry paths:

- **REMOTE** opens Spotify controls without changing the active external Spotify Connect device.
- **PLAY HERE** starts the ORC local Web Playback SDK device, transfers playback to it, and opens the same Spotify UI.

The Spotify screen also exposes **Liked Songs** and **Recently Played**. Collection retrieval runs on a worker thread and selecting a returned track queues playback through the shared Spotify service.

Because library/history permissions were added after the original playback integration, existing users must reauthorize Spotify once so the cached token includes the new scopes.

### Theme behavior

The Spotify theme adapter in `composition/media.py` derives chrome colors from the active CSS `ThemeBundle`. Backgrounds, surfaces, borders, text, and ordinary controls follow ORC dark/light mode. Intentional Spotify actions and progress accents use Spotify green (`#1DB954`) rather than ORC blue.

`SpotifyScreen` receives a theme provider and rebuilds its visible view when the theme changes. HOME now-playing also receives the live theme provider. Neither should initialize itself with a fixed dark palette. Theme changes must not create duplicate Spotify services or synchronously fetch playback state on the Tk event thread.

## Local Spotify playback

`SpotifyLocalPlayer` owns the local SDK host and browser backend. The browser is an audio implementation detail and is hidden after the SDK registers the `OpenRoadCode` Connect device. PLAYER mode is currently verified with Google Chrome stable on Debian/Ubuntu AMD64. Spotify Premium is required by the Web Playback SDK.

Termux remains REMOTE-only because its current Chromium environment does not provide the required Web Playback/EME capability.

## YouTube and Netflix

`YouTubePlayer` and `NetflixPlayer` own semantic browser-backed playback operations. `BrowserKioskLauncher` owns process lifecycle, and `X11WindowEmbedder` owns native reparenting into the ORC media surface.

Both services use persistent dedicated browser profiles so login state can survive application restarts. Netflix protected playback additionally requires browser Widevine/DRM support; Termux Chromium currently does not provide it.

### Browser color scheme

The media composition supplies a preferred color scheme derived from the active ORC theme. The managed browser launcher passes the corresponding Chromium/Blink preference at launch. Changing ORC dark/light mode while a browser screen is active relaunches that managed browser with the new preference and reloads its configured URL. The dedicated profile is preserved, so the theme transition does not intentionally clear authentication.

The Tk wrapper also repaints from the active CSS bundle. Browser preference and Tk chrome are separate concerns. The website controls its own final rendering, so a preferred color scheme does not guarantee that every website will honor the request. Avoid applying arbitrary CSS or color inversion to third-party pages.

## Configuration

Spotify secrets are installed separately from browser/media runtime dependencies:

```bash
./development/debian/install_secrets.sh
./development/debian/setup_media.sh
```

OAuth/token details live in `protocols/spotify/README.md`; application-facing Spotify behavior lives in `controllers/spotify/README.md`; browser-backed video behavior lives in `controllers/video/README.md`.

## Verification

From the repository root:

```bash
python -m unittest discover -s apps/orcUi/composition/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/media/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/radio/unit_test -p 'test_*.py'
python -m apps.orcUi
```

Check HOME and Spotify in both modes, provider-green actions, remote/local playback behavior where supported, YouTube and Netflix browser preferences, navigation between screens, and resource cleanup. The unit tests use mocks and do not prove Chromium, DRM, Spotify Connect, or X11 integration on a particular target.
