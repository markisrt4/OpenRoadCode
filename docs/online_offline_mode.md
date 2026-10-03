# ORC online and offline mode

Click the ONLINE/OFFLINE button in the top bar to change ORC's mode. The preference
is saved in `~/.config/openroadcode/online-mode.json` (or the configured XDG config
home) and restored on startup. A failed preference write leaves the existing mode
unchanged and displays an error in the shell status area.

Offline mode disables POI Order and Website buttons, Spotify, YouTube,
YouTube Music, Netflix, and internet radio. Entire streaming-provider and internet-radio cards grey out, including logos,
illustrations, accent bars, text, and buttons. Online mode restores their colors.
Streaming controls grey out, including
the home radio shortcut and Spotify account connection. Existing ORC browser
players and internet radio stop when switching offline. Spotify polling, remote
commands, and radio-directory requests are blocked. Switching online reenables
controls without automatically restarting playback.
An open POI card updates immediately when the mode changes. The action handler
also checks the mode before launching an external destination. Local POI search,
map display, and offline navigation remain available.

The four ascending Android-style bars show internet reachability, not cellular
or Wi-Fi signal strength:

- ONLINE with green bars: the internet check succeeded.
- ONLINE / CHECKING: awaiting a check result.
- ONLINE / NO NET: the check failed; online mode still permits attempts.
- OFFLINE with empty bars: online POI and streaming actions are disabled.

The check sends a bounded HTTPS HEAD request to Google's connectivity endpoint
(`connectivitycheck.gstatic.com/generate_204`) approximately every 30 seconds,
in a background thread. Offline mode starts no checks; a check already in flight
may finish, and its stale result is ignored. One reachable endpoint does not
establish that every restaurant or online provider is available.

This is an ORC feature preference, not the phone's airplane mode. Local
visualizers and RF radio remain available. The standalone POI downloader is not
yet connected to this preference. Requests already in flight may finish. Spotify playback on another
device is not forcibly stopped, because that requires an online API call. An
external browser or app already opened remains under its own lifecycle. Further internet-dependent features should share the same
`OnlineModeController` rather than maintain separate toggles.

Phone smoke test:

```bash
cd ~/src/OpenRoadCode
git switch android-linux-food-apps
git pull --ff-only origin android-linux-food-apps
./runOrcUi
```

Open a POI card with Order/Website actions and switch OFFLINE in the top bar.
Confirm those buttons grey out while Navigate remains enabled. Switch ONLINE
and confirm they reenable. Restart ORC in offline mode and confirm it is retained.

On MEDIA, switch OFFLINE and confirm streaming buttons grey out while the
visualizer remains available. On RADIO, confirm internet radio is disabled while
RF stays available. Start an internet stream online, switch offline, and confirm
it stops. Switch online and confirm playback requires a new selection.

Offline mode does not hide cached POI markers or disable Food/Fuel searches.
If markers are absent, the terminal reports the index path and viewport search
bounds/count. Database errors appear in the navigation status and keep the event
poll alive, so another search can retry after the data problem is corrected.

Weather follows the same mode: refresh is disabled offline, and the latest
forecast fetched during this ORC session remains visible with its full update
date and time and an Offline/Cached label. Starting offline without a forecast
shows “No cached weather available”; forecast data is not yet persisted across
ORC restarts. Switching online while Weather is open immediately reenables controls and
requests fresh data, bypassing the five-minute cache reuse window. The cached
forecast stays visible while the status reports refreshing. GPS lookup has a
two-second deadline, falling back to the last forecast location (or configured
location); the forecast HTTP request uses a five-second socket timeout. Failed
forced refreshes report an error while keeping the cached forecast visible.

The background NWS alert service reads the saved online preference before each
poll, so it must run as the same user with the same XDG configuration directory
as ORC. Offline polls do not request alerts or interpret the pause as an alert
withdrawal. Existing banners/details warn that cached alerts may be outdated;
normal local expiry still applies. Polling resumes at the next scheduled cycle
when online. An alert request already in flight may finish.

Weather smoke test: fetch a forecast online, switch offline, and confirm Refresh
is disabled, the cached label includes the update date/time, and NOAA RF remains
available. Switch online and confirm Refresh reenables. If an alert is displayed,
confirm its offline warning appears without hiding the alert.
