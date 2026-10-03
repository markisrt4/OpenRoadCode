# ORC online and offline mode

Click the ONLINE/OFFLINE button in the top bar to enable online features or
choose manual offline mode. A failed internet check automatically disables
online features; successful recovery reenables them. Manual offline mode stays
offline until you toggle it back. The preference
is saved in `~/.config/openroadcode/online-mode.json` (or the configured XDG config
home) and restored on startup. A failed preference write leaves the existing mode
unchanged and displays an error in the shell status area. For ordering and login
sessions, see [POI ordering](poi_ordering.md); for downloading local data, see
[Termux POI downloads](termux_poi_download.md).

Offline mode disables POI Order and Website buttons, Spotify, YouTube,
YouTube Music, Netflix, and internet radio. Entire streaming-provider and
internet-radio cards grey out, including logos, illustrations, accent bars, text,
and buttons. Online mode restores their colors.
Streaming controls grey out, including the home radio shortcut and Spotify account connection. Existing ORC browser
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
- OFFLINE / NO NET: the check failed; online actions are disabled while recovery checks continue.
- OFFLINE with empty bars: online POI and streaming actions are disabled.

The check sends a bounded HTTPS HEAD request to Google's connectivity endpoint
(`connectivitycheck.gstatic.com/generate_204`) approximately every 10 seconds,
in a background thread. Checks continue when offline was inferred from a failed
internet request or no local monitor is available. A definite local disconnect
suspends internet requests until the local monitor reports recovery or becomes
unavailable. Manual offline mode starts no internet checks. A check already in flight may finish, and results
from before a manual toggle are ignored. Detection depends on that endpoint
being reachable and returning HTTP 204;
a captive portal or a blocked endpoint can cause offline mode even if some sites
work. One reachable endpoint does not establish that every provider is available.

This is an ORC feature preference, not the phone's airplane mode. Local
visualizers and RF radio remain available. The standalone POI downloader is not
yet connected to this preference. Requests already in flight may finish. Spotify
playback on another
device is not forcibly stopped, because that requires an online API call. An
external browser or app already opened remains under its own lifecycle. Further
internet-dependent features should share the same
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
POI runtime diagnostics use the shared [structured logging infrastructure](../common/logging/README.md)
under the `navigation.poi` component prefix. ORC collects logs quietly by default.
Run `./runOrcUi --follow-logs` to display INFO messages, or
`./runOrcUi --follow-logs --log-level DEBUG --log-component navigation.poi`
to inspect POI details. INFO records index opening, result counts, and popup selection;
DEBUG records viewport bounds and detailed click/marker resolution. Malformed
click payloads are WARNING and database failures are ERROR. The application's
logging configuration controls which records are displayed or stored. Routine
records exclude coordinates and business names; malformed click warnings exclude
the raw payload. Database
errors also appear in the navigation status and keep the event poll alive, so
another search can retry after the data problem is corrected.

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

Automatic-mode smoke test: enable online features, then disable both Wi-Fi and
mobile data on the phone. Within the next check cycle, confirm the top bar shows
OFFLINE / NO NET and POI/streaming/weather controls disable. Restore internet and
confirm controls reenable without restarting ORC. Playback does not restart
automatically. Choose manual OFFLINE and confirm restoring internet leaves ORC
offline until you toggle it. Automatic and manual states survive ORC restarts;
background services read the effective `online` field while `requested_online`
retains the user's preference for automatic recovery.

## Faster local network detection

On Termux, ORC reads Android Bridge's `/network` endpoint on loopback port 8766
once per second. Bridge's default-network callbacks report INTERNET + VALIDATED
capabilities; losing either disables online features on the next UI poll, usually
within one to two seconds after Android reports the change. Install the updated
Bridge APK on `host-actions` and keep its Sensor Bridge service enabled. An older
APK, stopped service, or unavailable monitor returns ORC to internet-check
fallback without declaring the whole phone disconnected merely because Bridge
is unavailable. Local checks bypass HTTP proxies. No additional port is needed.

On Linux, ORC uses `nmcli monitor` to receive NetworkManager D-Bus changes and
queries the local STATE/CONNECTIVITY properties when an event arrives. No Python
D-Bus dependency is needed. Missing nmcli or NetworkManager leaves periodic
internet checks active. If the monitor exits, ORC falls back and retries the
monitor after five seconds; it stops the child process when ORC closes.

A definite local loss immediately disables features and invalidates any internet
check from before that loss. A recovery event starts an internet check immediately
instead of waiting for the periodic timer. An in-flight request may still take up
to three seconds to finish before that new check starts. NetworkManager reporting
unknown connectivity on a connected interface still requires internet checks;
this also covers Linux tethering whose local link survives upstream mobile-data
loss. Manual OFFLINE always retains priority.

Phone update (wait for the build for the new commit to succeed, so the installer
does not select an older successful APK):

```bash
cd ~/src/openroadcode-android-bridge
git switch host-actions
git pull --ff-only origin host-actions
./development/termux/install_latest_apk.sh
```

Open Android Bridge after installing and enable Sensor Bridge. Verify
`http://127.0.0.1:8766/network` returns JSON with `available: true`. Update ORC
using the commands above. Turn off both Wi-Fi and mobile data and confirm a much
faster automatic offline transition; restore internet and confirm automatic
recovery. On Linux with NetworkManager, disconnect/reconnect Wi-Fi or Ethernet
and confirm the same behavior.
