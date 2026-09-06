# Video Controllers

`controllers/video` contains application-facing video behavior used by OpenRoadCode. Browser process mechanics remain in `apps/launchers`; X11 window ownership/reparenting remains in `frontends/x11`; `apps/orcUi` owns the integrated presentation.

## YouTube

`YouTubePlayer` opens YouTube in a dedicated browser application window using a retained profile. It accepts either a YouTube HTTPS URL or a search query, validates direct URLs, and delegates browser lifecycle to `BrowserKioskLauncher`.

`YouTubeMusicVideo` and `MusicVideoController` provide the Spotify-to-music-video path. The controller maps the current Spotify track to a YouTube search/playback target without making Spotify UI code responsible for browser details.

The ORC Media page reparents the YouTube browser window into its X11 host where supported.

## Netflix

`NetflixPlayer` opens validated Netflix HTTPS URLs in a dedicated retained browser profile and delegates process lifecycle to `BrowserKioskLauncher`. The ORC Media page can host that window inside the X11 media surface.

Netflix playback depends on browser DRM/EME support. A browser being able to render the Netflix site does not imply it can decode protected video. In particular, the current Termux Chromium path lacks Widevine and therefore cannot provide Netflix video playback. Supported desktop/embedded targets must provide a browser with the required DRM capability.

## Browser profiles

YouTube and Netflix intentionally use dedicated persistent browser profiles so login/session state can survive ORC restarts. Profile data is runtime state and must not be committed to the repository.

## Theme and rendering

The players accept dark-mode and software-rendering options. `orcUi` selects these according to the active ORC theme and runtime target. Browser flags are implementation details of the video controllers/launcher boundary, not UI policy.

## Tests

Unit tests live under `controllers/video/unit_test`. Browser/component tests may require an active X11 display and installed browser and should remain separate from pure unit tests.
