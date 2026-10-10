# Spotify UI ownership

The ORC Spotify home summary, playback panel, library browser, and video overlay
consume toolkit-independent contracts in `ui/media/spotify_presentation_if.py`
and `ui/media/spotify_browse_if.py`. Snapshots are immutable. Playback positions
and durations remain seconds; Tk owns time formatting, image decoding, layout,
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

`MediaScreen` account setup still owns its legacy worker and remains a separate
boundary exception. This migration does not claim completion of every media or
repository UI boundary. The historical master audit remains historical.
