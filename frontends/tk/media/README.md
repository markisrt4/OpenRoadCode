# ORC Media Integration

The `orcUi` Media surface integrates Spotify, YouTube, YouTube Music, and Netflix while keeping service protocols, browser lifecycle, X11 mechanics, and Tk presentation separated. See [`apps/orcUi/ARCHITECTURE.md`](../../../apps/orcUi/ARCHITECTURE.md) for the complete application composition and ownership model.

## Composition and ownership

`apps/orcUi/composition/media.py` constructs the media presentation graph using the shared `OrcUiApplicationRuntime`. It wires the MEDIA hub, Spotify screen, browser-backed screens, HOME now-playing widget, image cache, lyrics client, and music-video controller. `MediaComposition.close()` releases its owned music-video resource. The application runtime owns shared media services and managed application launchers. HOME and MEDIA must not create separate Spotify state services.

The media navigation bar provides navigation between the hub, Spotify, YouTube, Netflix, and HOME. Individual provider screens do not need duplicate provider-selection buttons.

## Spotify

The hub's Spotify header presents cached now-playing title, artist, and 56-pixel
album artwork through `ui/media/media_preview_if.py`. With no track, it shows a
Spotify placeholder. `MediaPreviewController` shares the existing service and
image cache through composition, loads PNG artwork on its own worker, suppresses
obsolete requests and shutdown completions, and honors offline policy. Tk only
decodes returned bytes and renders them; it ignores stale artwork, cancels polling
on hide/destroy, and rebuilds from the active theme. Existing Remote, Play Here,
account, and setup actions remain available. No extra card row is introduced.

`SpotifyStateService` owns the shared background controller used by Home and Media. It serializes Web API access, caches now-playing state, and keeps network/control operations off the Tk event thread.

The Media landing card offers two entry paths:

- **REMOTE** opens Spotify controls without changing the active external Spotify Connect device.
- **PLAY HERE** starts the ORC local Web Playback SDK device, transfers playback to it, and opens the same Spotify UI.

The Spotify screen also exposes **Liked Songs** and **Recently Played**. Collection retrieval runs on a worker thread and selecting a returned track queues playback through the shared Spotify service.

Now Playing reserves the available height for album art, metadata, and lyrics:
Media return sits beside Disconnect in the setup row. Watch Video (with a
code-drawn YouTube icon) and Visualizer share the lower utility row. Watch Video
uses 13-point text centered between equal side columns; device status aligns
right. The panel omits duplicate volume controls in favor of the persistent
shell volume widget. Previous, Pause/Play, Next, and ±10-second controls have
taller raised bezels. Compact ±10-second controls use
the existing relative seek contract; the same service supports 30-second seeks
without a new API. The library view retains its existing navigation bar.

Because library/history permissions were added after the original playback integration, existing users must reauthorize Spotify once so the cached token includes the new scopes.

### Theme behavior

The Spotify theme adapter in `apps/orcUi/composition/media.py` derives chrome colors from the active CSS `ThemeBundle`. Backgrounds, surfaces, borders, text, and ordinary controls follow ORC dark/light mode. Intentional Spotify actions and progress accents use Spotify green (`#1DB954`) rather than ORC blue.

`SpotifyScreen` receives a theme provider and rebuilds its visible view when the theme changes. HOME now-playing also receives the live theme provider. Neither should initialize itself with a fixed dark palette. Theme changes must not create duplicate Spotify services or synchronously fetch playback state on the Tk event thread.

## Local Spotify playback

`SpotifyLocalPlayer` owns the local SDK host and browser backend. The browser is an audio implementation detail and is hidden after the SDK registers the `OpenRoadCode` Connect device. PLAYER mode is currently verified with Google Chrome stable on Debian/Ubuntu AMD64. Spotify Premium is required by the Web Playback SDK.

Termux remains REMOTE-only because its current Chromium environment does not provide the required Web Playback/EME capability.

## Media hub and YouTube Music

The Media landing page is a four-card hub for Spotify, YouTube, YouTube Music, and Netflix. Provider identity colors are accents, not replacement theme surfaces: card backgrounds, text, and ordinary controls continue to follow the active ORC light/dark theme.

The left column groups music services and a compact Music Visualizer tile below
YouTube Music; video services occupy the right column. The visualizer tile uses
a responsive teal, blue, and violet spectrum illustration and remains available
offline. The illustration is decorative; live visualization opens through the
existing visualizer action. It redraws on allocation changes without animation
timers or audio subscriptions. Provider brand colors
stay in their logos, with neutral action buttons and muted Coming Soon text for
YouTube Music. Provider
headers add a soft green, crimson, coral, or burgundy wash that fades from the
larger logo into the theme surface. Hover highlights the card edge subtly;
neither treatment changes provider actions or loads bitmap assets. Provider
cards use consistent compact logos, titles, descriptions that wrap to their
allocated width, and action buttons. Spotify groups app setup and account access
in one secondary row inside the card body, separate from Remote and Play Here.
These controls emit `SpotifyAccountSession` requests and retain offline restrictions;
composition owns account workers and the configuration dialog.
The online hub clears its footer status on entry; the offline explanation remains.

YouTube Music is intentionally advertised ahead of its runtime integration. Selecting it opens a dedicated **Coming Soon** screen. It must not construct a managed browser player or reference an `youtube_music` application-runtime key until that launcher is actually registered. This keeps the planned feature visible without creating a false runtime dependency.

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
