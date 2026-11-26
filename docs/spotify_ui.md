# Spotify UI ownership

The ORC Spotify home summary, playback panel, library browser, and video overlay
consume toolkit-independent contracts in `ui/media/spotify_presentation_if.py`,
`ui/media/spotify_browse_if.py`, and `ui/media/spotify_account_if.py`. Snapshots are
immutable. Playback positions and durations remain seconds; Tk owns time formatting, image decoding, layout,
artwork resizing, accent colors, and toolkit image lifetimes.

`SpotifyPresentation` owns presentation polling, artwork and lyric loading,
lyric selection, video availability and playback requests, optimistic volume
confirmation, and delivery generations. It delegates playback commands to the
shared `SpotifyStateService`, which keeps network calls off the frontend thread.
`SpotifyBrowser` owns collection and playlist queries, cache selection, card
artwork, local/remote destination requests, and stale completion rejection.
The local player state and destination enum now live under `ui/media`; existing
controller imports remain aliases for compatibility.

Composition constructs services, sessions, a bounded presentation worker pool,
and native adapters. Hiding a screen retires request bindings and timers before
its Tk hosts are destroyed, without stopping shared Spotify playback. Closing
composition retires the screen and sessions before stopping workers and music
video playback. A destroyed home summary closes and releases its session.
Workers enqueue Python-only frontend callbacks; view and collection/track
checks reject deliveries after hide, close, offline transitions, and replacement.
In-flight video launches receive a cancellation predicate and stop/restore
Spotify if the presentation retires during launch.

The shared Car UI screen caller is wired through
`apps/carUi/composition/spotify.py` and retains its audio-volume fallback.
No dependencies are constructed in `UiWidget`, which remains only a policy marker.

## Validation and device acceptance

Contract tests cover stale collection, artwork, lyric, and video results; hide and
terminal close; playlist drilldown; cached browsing; offline transitions; local
player availability; and rapid volume intent. Strict mypy includes the migrated
contracts, controllers, widgets, and session factories. Static bindings check
implementations against their presentation and lifecycle contracts.

Live acceptance still needs Spotify authentication, liked/recent/playlist
browsing, remote and local playback transfer, rapid volume clicks, seeking,
artwork and lyrics, video start/return, theme rebuilds, and navigating away during
loading. Verify X11 detachment before destroying video hosts. The previously
required live RF/X11 acceptance remains a prerequisite for merging this branch.
The full integration gate may fail under sandbox restrictions, including native
ZeroMQ socket creation; a passing portable suite does not replace device checks.

## Account setup and cancellation

`SpotifyAccountController` owns configuration reads/writes, sign-in, disconnect,
shared immutable account state, and worker-to-frontend delivery. Media and Spotify
screens have independent request bindings. Composition owns a separate bounded
account worker pool, token/secret services, and the shared Tk configuration dialog.
The dialog only collects the public client ID and renders state; no token or client
secret enters a presentation snapshot. Configuration still requires an ORC restart.

Hiding a view cancels its authorization request; closing composition invalidates
all requests before worker shutdown. Offline transitions and disconnect also
supersede sign-in. OAuth callback waits poll cancellation and release their local
listener. Token persistence is serialized with request cancellation, so a token
exchange completing after retirement cannot overwrite a subsequent disconnect.
Results never navigate back to Media. Account contract tests cover these lifetimes,
configuration errors, retry, multiple views, and local listener cancellation.
Live acceptance includes navigating away during sign-in and restarting sign-in
without a callback-port conflict.

Fourteen pre-existing boundary exceptions remain across the repository. The
historical master audit remains historical.

## Local player on Raspberry Pi

ORC PLAYER uses the Spotify Web Playback SDK in a separate browser profile.
The SDK helper starts minimized. Playback controls and track information stay
in ORC. A Spotify artist search from Trending opens the provider browser.
It requires a Spotify Premium account and working protected audio support in
that browser. If initialization fails, ORC checks whether the profile can
access Widevine and reports a more specific error when it cannot. If the SDK
itself fails to download, check internet access from the Pi's browser.

To isolate a browser playback failure, open `https://open.spotify.com` in
Chromium on the Pi desktop and try playing a track. If Chromium reports that
protected content is unavailable, check its protected-content settings and
Widevine support for your Raspberry Pi OS release. On Raspberry Pi OS
Bookworm and Trixie, the Raspberry Pi APT archive provides
`libwidevinecdm0`. Check availability with `apt-cache policy libwidevinecdm0`
and install it with `sudo apt install libwidevinecdm0` if missing. Fully quit
Chromium and ORC before retesting. If the web player works
but ORC still fails, retry ORC PLAYER and record the exact ORC popup text.
During troubleshooting, Trending can play on an available Spotify Connect
device controlled from ORC.

After connecting your Spotify account, open **Settings → Media → Spotify**
and tap **Test local player**. ORC enables encrypted media in its dedicated
Chromium profile and checks Widevine before loading the Spotify playback SDK.
When the device registers, choose a track and check for audio. Account
authorization is required, and registering the local player can transfer
current playback to the Pi.
