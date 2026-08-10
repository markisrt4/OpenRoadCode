# Weather Controller

`controllers/weather` retrieves and persists weather independently of
Streamlit, Tkinter, or any other frontend.

## Components

- `WeatherSnapshot` is the typed location, retrieval time, and forecast.
- `WeatherSnapshotCache` owns JSON serialization and validation.
- `OpenMeteoWeatherController` owns Open-Meteo requests and freshness policy.
- `GpsdWeatherLocationProvider` preserves GPS-based location when a fix exists.
- `PersistentCache` supplies atomic byte storage underneath the domain cache.

CarUi refreshes a snapshot in a daemon worker after normal startup. The
weather Streamlit process reads the same disk cache, allowing it to render the
latest forecast without repeating location, reverse-geocoding, and forecast
requests during its initial browser session.

CarUi prefers a GPSD fix and falls back to the configured controller location
when GPSD or a fix is unavailable. Reverse geocoding is intentionally absent
from the launch path; GPS coordinates remain visible as the location name.
When enabled, CarUi also checks the shared last-known position snapshot before
falling back to static coordinates.

The default cache is:

```text
~/.cache/openroadcode/weather
```

If a refresh fails, `refresh_if_stale()` returns an older snapshot when one is
available. This provides useful offline behavior while preserving the age in
`WeatherSnapshot.fetched_at`.

Run its tests from the repository root:

```bash
venv/bin/python -m unittest discover \
  -s controllers/weather/unit_test -p 'test_*.py'
```
