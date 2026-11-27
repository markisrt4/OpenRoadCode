# Self-host MusicForge Airplay for ORC Trending

ORC reads charts from an Airplay-compatible HTTP service. The server needs a
source of airplay observations, such as a collector that records track, artist,
station and timestamp. Run the collector and chart API on your server, with
persistent storage for the observations. OpenRoadCode and libMusicForge do not
ship the VPS collector or chart API, so deploy your own implementation or an
existing compatible service. The following describes the interface it must
provide and how to connect it to ORC.

## Server endpoints

Return JSON with a successful HTTP status for these requests.

| Request | Example response |
| --- | --- |
| `GET /health` | `{"status":"ok"}` |
| `GET /api/v1/stations` | `{"stations":[{"station":"Example FM"}]}` |
| `GET /api/v1/charts/songs` | `{"results":[{"title":"Example Song","artist":"Example Artist","plays":12}],"coverage":"7 days"}` |
| `GET /api/v1/charts/artists` | `{"results":[{"artist":"Example Artist","plays":12,"songs":3}],"coverage":"7 days"}` |

For both chart endpoints, accept `period=today|7d|30d`, an optional `station`
matching a station-list entry, and a numeric `limit`. Filter plays for the
requested period and station, group by track and artist for songs or by artist
for artists, and return the highest play counts first. When a period has no
data, return an empty `results` array. The optional `coverage` field describes
how much data the server observed.

For a private VPS, run the API on the VPS loopback interface, for example
`127.0.0.1:8003`. Allow the tunnel account to forward to that address and port
in OpenSSH. On the VPS, check `/health` and fetch
`/api/v1/charts/songs?period=7d&limit=5` from the loopback URL before configuring
the Pi. For a direct internet connection, serve the API over HTTPS.

## Connect the Pi

Run the OpenRoadCode Linux installer TUI as the user who runs ORC. At the
optional **Trending music** step, choose one of these connection types.

- **Direct API** saves the API base URL, for example
  `https://airplay.example.com`.
- **Private SSH tunnel** asks for a VPS login such as `airplay@vps.example.com`,
  the SSH port, and the VPS API port. The default VPS API port is `8003`.
  If your one-time VPS login uses a private key, enter its path on the Pi.

On a first-time SSH connection, compare the displayed SSH host fingerprint to
your server's fingerprint before accepting it. The tunnel setup registers
only the Pi's public key on the VPS and restricts it to forwarding to the API.
Its private key stays at `~/.ssh/id_ed25519_musicforge_tunnel` on the Pi. The user
service is enabled at login and reconnects on failure. Enable systemd lingering
for the ORC user if the tunnel must run before login.

To configure a previously installed Pi from the command line, run from the
OpenRoadCode checkout. Substitute your own server address and ports.

```bash
bash scripts/systemd/install_musicforge_airplay_tunnel.sh airplay@vps.example.com 22 8003
```

For a direct connection, use:

```bash
python3 -m scripts.installers.setup_musicforge_airplay https://airplay.example.com
```

Setup verifies the station endpoint before saving the base URL in
`${XDG_CONFIG_HOME:-$HOME/.config}/openroadcode/musicforge-airplay-url`. In tunnel
mode this URL is `http://127.0.0.1:8003`. ORC reads it on startup, including desktop
autostart. An explicit `MUSICFORGE_AIRPLAY_URL` environment variable still takes
precedence.

## Verify and migrate

For a tunnel, confirm the user service is active and the Pi can fetch charts.

```bash
systemctl --user is-active musicforge-airplay-tunnel.service
curl -fsS 'http://127.0.0.1:8003/api/v1/charts/songs?period=7d&limit=5'
```

Then restart ORC, go online, and open **Radio → Trending**. If the SSH connection
fails, inspect `systemctl --user status musicforge-airplay-tunnel.service` and
`journalctl --user -u musicforge-airplay-tunnel.service`.

On an existing Pi, enter the same VPS address and ports to reuse the installed
tunnel and key. If the configured service needs to change, the helper asks
before replacing it and keeps a backup. Switching to a direct URL leaves the
existing tunnel service available. If it is no longer needed, stop and
disable it with `systemctl --user disable --now musicforge-airplay-tunnel.service`.
