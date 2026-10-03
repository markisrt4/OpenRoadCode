# ORC online and offline mode

Click the ONLINE/OFFLINE button in the top bar to change ORC's mode. The preference
is saved in `~/.config/openroadcode/online-mode.json` (or the configured XDG config
home) and restored on startup. A failed preference write leaves the existing mode
unchanged and displays an error in the shell status area.

In this first integration, offline mode disables POI Order and Website buttons.
An open POI card updates immediately when the mode changes. The action handler
also checks the mode before launching an external destination. Local POI search,
map display, and offline navigation remain available.

The four ascending Android-style bars show internet reachability, not cellular
or Wi-Fi signal strength:

- ONLINE with green bars: the internet check succeeded.
- ONLINE / CHECKING: awaiting a check result.
- ONLINE / NO NET: the check failed; online mode still permits attempts.
- OFFLINE with empty bars: POI online actions are disabled.

The check sends a bounded HTTPS HEAD request to Google's connectivity endpoint
(`connectivitycheck.gstatic.com/generate_204`) approximately every 30 seconds,
in a background thread. Offline mode starts no checks; a check already in flight
may finish, and its stale result is ignored. One reachable endpoint does not
establish that every restaurant or online provider is available.

This is an ORC feature preference, not the phone's airplane mode. Media streaming,
weather providers, and the standalone POI downloader have not yet been connected
to this preference. An external browser or app already opened remains under its
own lifecycle. Further internet-dependent features should share the same
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

Offline mode does not hide cached POI markers or disable Food/Fuel searches.
If markers are absent, the terminal reports the index path and viewport search
bounds/count. Database errors appear in the navigation status and keep the event
poll alive, so another search can retry after the data problem is corrected.
