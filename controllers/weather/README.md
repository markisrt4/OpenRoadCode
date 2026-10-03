# Weather

`controllers/weather` owns provider-independent Weather domain state, location
resolution, forecast orchestration, presentation mapping, and weather-alert
domain models. Provider transports live below the `WeatherProviderIf` boundary;
concrete UI rendering remains outside the controller package.

## Forecast architecture

The forecast path is:

```text
GPSD current position
        |
        v
WeatherController
        |
        +--> configured navigation fallback when GPS/fix is unavailable
        |
        v
WeatherProviderIf
        |
        v
OpenMeteoWeatherProvider
        |
        v
normalized SI WeatherState
        |
        v
WeatherPresenter
        |
        v
WeatherUiIf / native Tk Weather screen
```

`WeatherState` is provider-independent and normalized to SI units. Temperature
is stored in kelvin, pressure in pascals, wind speed in meters per second,
precipitation in meters, and ratios such as humidity and precipitation
probability are normalized to 0..1. Imperial/Metric conversion belongs at the
presentation boundary rather than in providers or domain state.

`WeatherController` retains the latest in-memory state and supports a stale-age
policy. A failed refresh may return the existing state when one is available,
so a transient network failure does not unnecessarily replace useful Weather
data.

The current orcUi composition selects `OpenMeteoWeatherProvider`. The provider
contract intentionally permits additional forecast providers without making
the UI provider-specific.

## Location

orcUi uses `GpsdWeatherLocationProvider` for current vehicle position. If GPSD
or a usable fix is unavailable, composition falls back to the configured
navigation simulation/fallback coordinates from the shared runtime
configuration.

Location acquisition is separate from forecast providers. Providers receive a
`WeatherLocation`; they do not own GPS hardware or navigation state.

## Native orcUi presentation

The reusable Tk Weather screen lives under `frontends/tk/weather`. It performs
forecast refresh work off the Tk event thread and presents the most recently
available state while a refresh is in progress.

The native dashboard presents current conditions plus hourly and daily
forecasts. Global Imperial/Metric preference is supplied by application
composition from `common.app_settings`; the Weather domain remains SI.

The semantic NOAA Weather Radio action is composed by orcUi through the existing
radio profile/controller path. Weather presentation does not own SDR++ process
lifecycle or RF tuning infrastructure.

## Weather alerts

Forecast retrieval and severe-weather alerts are separate paths. NWS alerts use
`NwsWeatherAlertProvider` and the long-lived runtime under
`services/weather`.

```text
navigation position telemetry
        |
        v
WeatherAlertRuntime
        |
        v
NwsWeatherAlertProvider
        |
        v
weather.alert ZeroMQ contract
        |
        v
orcUi StateIngressRuntime
        |
        v
WeatherAlertPresenter
        |
        v
OrcUiPresentationState
        |
        v
persistent shell alert banner
```

Alert lifecycle identity has two distinct fields:

- `identifier` is the provider-owned opaque alert identifier.
- `correlation_id` is ORC-owned and identifies one observed alert lifecycle.

Operations are `ACTIVE` and `CLEARED`. A first observation publishes ACTIVE
with a new correlation ID; changes to the same provider alert remain ACTIVE with
that correlation ID. A disappearance publishes CLEARED. Normal provider-declared
expiration uses `EXPIRED`; an alert that disappears before expiration uses
`WITHDRAWN`. `CANCELLED` is part of the domain contract but is not currently
emitted by the runtime.

The alert message schema is version 1. Countdown presentation is derived locally
from the provider-declared `expires_at` timestamp rather than being transmitted
as changing countdown state.

Correlation IDs are currently in-memory runtime state and therefore are not
preserved across service restarts.

## Component test

A direct Open-Meteo component-test CLI is available:

```bash
python -m controllers.weather.component_test.open_meteo_provider_cli
```

It performs a real provider request and therefore requires network access.

In the integrated Tk navigation screen, the radar menu opens a collapsible
history panel. Play/Pause loops through cached frames; dragging the timeline
pauses playback and selects a frame directly. Live refreshes the latest frame.
Playback speed choices are in Options; Classic colors has a separate toggle
below the replay controls. Collapsing the panel keeps
radar visible and allows playback to continue; turning radar off or leaving
Navigation stops playback. The cloud button beside the menu controls visibility.

The experimental HRRR forecast toggle selects NOAA's CONUS simulated composite
reflectivity for the next six hours. Forecasts open at the nearest future frame,
are labeled Forecast with their lead time, and use Now to return to observed
RainViewer radar. HRRR is model output, not a future radar observation; coverage
is the contiguous United States. Forecast availability depends on NOAA's public
HRRR archive. Missing forecasts and dependencies are reported as unavailable.

Forecast playback waits for outstanding local tile downloads and decoding before
starting each frame's display interval. The panel shows Loading while waiting;
tile failures or a two-minute timeout pause playback with an explanation.

The provider reads GRIB2 indexes from
`https://noaa-hrrr-bdp-pds.s3.amazonaws.com`. It selects one recent model run with
all six future hourly fields and falls back to an older complete run while a new
cycle is still publishing. HTTP byte-range requests download only the REFC
entire-atmosphere composite-reflectivity message, with a 16 MB limit; servers that
ignore the range are rejected. GDAL decodes each field once to a cached GeoTIFF
and reprojects visible 256-pixel tiles to Web Mercator. Pillow applies the radar
palettes. Native work is serialized with a 64 MB GDAL cache to limit phone memory
use; two decoded model runs are retained. Source-specific tile keys prevent
observed and forecast data from colliding. Older source downloads cannot overwrite
a newly requested source.

HRRR requires native GDAL with the GRIB driver. Termux supplies it through:

```bash
pkg install -y gdal
gdalinfo --formats | grep GRIB
```

Python GDAL bindings are not required, and the map renderer need not be rebuilt.
The first tile of a new forecast takes longer while its field is downloaded and
decoded. GRIB files and decoded model fields are cached beneath the radar cache.

Probe live NOAA metadata and raw reflectivity decoding before diagnosing map
rendering:

```bash
python -m controllers.weather.component_test.hrrr_radar_provider_cli
```

The probe prints the selected model run and valid times, downloads one indexed
reflectivity field, checks GRIB2 framing, runs the native decoder and reprojection,
and saves a forecast PNG under `~/.cache/openroadcode`. NOAA's ArcGIS image-server
catalog does not expose HRRR reflectivity and is not used by this integration.
The probe reports model coverage, the percentage of covered pixels with visible
reflectivity (at least 5 dBZ), and the maximum dBZ. Clear data is distinguished
from an entirely uncovered tile, which fails the probe. It defaults to the cached
GPS location when available; otherwise it identifies its central-US diagnostic
area explicitly. Use `--location LATITUDE LONGITUDE` to choose an area and
`--frame 1` through `--frame 6` to check other forecast hours.

Radar has two focused component tests:

```bash
python -m controllers.weather.component_test.rainviewer_radar_provider_cli
python -m controllers.weather.component_test.radar_map_overlay_cli --seconds 15
```

The first validates live radar metadata and the XYZ tile template. The second
requires the ORC broker and native map renderer; it publishes the newest radar
frame, leaves it visible briefly, then hides the overlay without discarding the
runtime radar source.

## Focused tests

From the repository root:

```bash
python -m unittest discover -s controllers/weather/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/weather/providers/unit_test -p 'test_*.py'
python -m unittest discover -s services/weather/unit_test -p 'test_*.py'
python -m unittest discover -s messaging/contracts/weather/unit_test -p 'test_*.py'
```

Repository quality gates additionally validate Doxygen contracts, generated
documentation, Markdown links, Mermaid conventions, lint, module size, the full
unit/integration suites, shell syntax, whitespace, and source-tree runtime
state.

In Navigation, **Weather → Along my route** opens a compact route forecast panel. Start a route
using a destination/POI, then enable **Weather on my route**. Up to six purple
checkpoints show Open-Meteo hourly forecasts for estimated arrival times, with
independent **Temp**, **Precip %**, and **Wind** label switches. Radar visibility
is independent, so forecast markers can appear with or without observed/HRRR
radar. The panel lists the checkpoint numbers, local arrival times, conditions,
and selected values; longer trips use a scrollable list.

Arrival times use calculated maneuver durations where complete, falling back to
distance-proportional route duration. They exclude live traffic and stops.
Refresh uses guidance progress to sample the remaining route; while Navigation
is visible, enabled route weather refreshes every 15 minutes. Refresh manually
after a major delay. Starting a new route, cancellation, and route completion
clear old markers; late results cannot replace a newer route. Missing values
appear as unavailable rather than zero. Forecast errors clear old values and
show an explanation. Forecasts require Internet access and available hourly data;
these layers are route checkpoint forecasts, not full-map temperature/wind grids.

To check real arrival-time data independently of the UI:

```bash
python -m controllers.weather.component_test.route_weather_provider_cli --location 42.8 -83.02 --hours 2
```

The map renderer must be rebuilt for the `set_route_weather` command and marker
layers. Existing styles gain an independent source at startup, so map data does
not need to be downloaded again.

Navigation's top bar groups Home/Work favorites and a **Places** search menu on
the left, with **Weather**, radar replay, and the quick radar toggle on the right.
**Clear place results** belongs to Places. The lower bar contains route guidance,
**End route**, and **Simulate**; it no longer mixes POI clearing with route actions.

**Weather → Map overlays** offers one full-area HRRR heatmap at a time:
**Temperature** (2 m air temperature) or **Wind speed** (10 m horizontal speed).
These use the nearest future hourly forecast from a recent CONUS model run and
show a forecast-valid time and palette legend in the selected unit system.
Wind speed is computed from both UGRD and VGRD components; these are heatmaps,
not wind-direction arrows. Radar and route forecast markers remain independent.
Model heatmaps refresh every 15 minutes while Navigation is visible, with manual
refresh available. They retain the camera and render beneath radar and route
information. GDAL and Internet access are required, as with HRRR reflectivity.
Outside model coverage, missing data stays transparent. Source/decoding failures
hide the model overlay and show an unavailable message.

Check either real model layer independently of GPU rendering:

```bash
python -m controllers.weather.component_test.hrrr_map_layer_cli --kind temperature --location 42.8 -83.02
python -m controllers.weather.component_test.hrrr_map_layer_cli --kind wind --location 42.8 -83.02
```

Rebuild the native navigation stack for the new `set_weather_field` command.
The model field cache shares recent-run retention with HRRR radar and downloads
only the selected GRIB messages, not whole forecast files.


### City weather

Navigation → **Weather → City weather** adds large weather values and city names
above radar and heatmaps. It remains independent of route weather and does not
move the camera. Cities come from the current offline map viewport: pan or zoom
to choose an area. Major cities get priority; spacing and a twelve-city limit
keep labels from crowding the map. At street zoom there may be no named city in
view; zoom out. The time caption stays on the map when the controls are closed.

Choose **Temp**, **Wind speed**, or **Precip total**, then **Recent history** or
**Forecast** and 1–24 hours. Temperature and wind show the selected hour before
or after the latest full UTC hour. Precipitation is a sum over the selected
window ending at that hour for history, or starting at that hour for forecast.
Totals include rain and the water equivalent of snow. All hourly calculations
use UTC; captions show local dates, times and timezone, including overnight
windows. Missing snapshots or incomplete totals show `—`, never an invented
zero. Fahrenheit/mph/inches or Celsius/km/h/mm follow the application's units.

Open-Meteo supplies these hourly model estimates; **Recent history is not a
weather-station observation archive**. A single batch fetch covers up to twelve
cities with two past days and three forecast days. Switching fields, scrubbing,
and playback reuse the downloaded hours. A bounded city cache reuses recent
locations when panning back. Refresh is automatic every fifteen minutes while
Navigation is visible, with a one-minute retry delay on provider errors.
**Play** animates cached hourly values independently of radar playback; hiding
Navigation pauses playback and viewport polling and clears city labels from the
map. Returning restores the selected view.

Rebuild the native navigation stack for city query and label commands. To check
live data separately from the GPU/UI:

```bash
python -m controllers.weather.component_test.city_weather_provider_cli --location 42.3314 -83.0458 --name Detroit
python -m controllers.weather.component_test.city_weather_provider_cli --kind precipitation --period past --hours 24
python -m controllers.weather.component_test.city_weather_provider_cli --kind wind --period future --hours 6
```

Attribution: [Open-Meteo](https://open-meteo.com/) weather data and offline
OpenStreetMap city names. The map overlay is a regional overview rather than
turn-by-turn weather guidance.


### Enforced weather UI boundary

Weather overlay widgets and Navigation radar controls consume contracts from
`ui/weather`: immutable overlay/radar state plus semantic request interfaces.
Controllers own provider access, worker threads, cache validity, viewport
queries, replay timers, readiness checks and periodic refresh. Composition owns
construction and cleanup; a screen closing cannot skip controller cleanup.
Tk views receive snapshots and emit requests. They cannot inspect provider
caches or send renderer commands.

City and route snapshots use Kelvin, metres/second, precipitation metres,
probability fractions and geographic radians. They carry aware UTC times.
`frontends/common` converts these values to display units/local time and adapts
state to native GeoJSON/raster commands. The same controller snapshots can feed
a non-Tk frontend without changing weather orchestration. Radar color choices
are defined in `ui/weather` rather than imported from a weather backend.

`python scripts/check_weather_ui_contracts.py` checks weather frontend imports,
backend-object access and controller independence from GUI frameworks. The local
quality gate and GitHub quality workflow both run it. ABC request/view contracts
reject incomplete implementations, binding checks reject unrelated backend
objects, and contract tests cover SI normalization, immutable snapshots,
semantic actions and lifecycle behavior. This is weather-specific enforcement;
it does not claim universal static type checking for every UI feature.

The forecast screen also uses `WeatherScreenUiIf` and
`WeatherScreenRequestHandlerIf`. `WeatherScreenController` owns refresh workers
and rejects stale completions after hiding or closing the screen. Tk receives
SI forecasts, loading state, and status through the contract.

## Data reliability and status

Radar replay distinguishes metadata refresh, waiting for imagery, downloads in
progress, loaded imagery, and unavailable imagery. The last successful metadata
check appears separately from the selected frame's valid time. A failed tile
remains failed until that same request succeeds; another successful tile cannot
hide the failure. Playback waits for downloads and pauses on a tile failure.
Explicit frame selection or refresh retries a failed frame with a new renderer
URL while retaining valid disk cache entries.

Downloaded and cached PNGs are validated before use. Corrupt cache entries are
removed and fetched again; invalid responses are not cached. Fully transparent
images display **Loaded tiles have no visible echoes**. This describes downloaded
tiles, not proof of dry weather, complete viewport coverage, or model coverage.

Observed radar is labelled old when the newest available source frame is more
than 30 minutes old, independently of the history frame selected. Forecast radar
labels an ended forecast period; this does not measure model-run freshness.
Status monitoring stops when Navigation is hidden or closed.

The Weather screen retains readable saved data when a refresh fails and labels
its age once it exceeds five minutes. Data also ages while the screen remains
open; status checks do not initiate network requests. A first-load failure shows
**Unavailable** and **Try Refresh** instead of a permanent loading placeholder.

Unit tests cover partial tile failures, localhost HTTP responses, transparent
and malformed PNGs, corrupt-cache recovery, retry URLs, data age, and callbacks
after hide/close. Status crosses the UI boundary through `RadarUiState`; widgets
perform presentation and time formatting without accessing tile services.

## City weather details

With **Weather → City weather** enabled, click a displayed city weather label or
point to open its details. The popup shows temperature and wind at the selected
hour, precipitation over the selected 1–24 hour window, and scrollable hourly
values for the displayed past or forecast period. Past values are model
estimates, not station observations. Hourly precipitation belongs to the hour
ending at that row's timestamp; the summary is a window total. Missing values
remain unavailable (—), rather than becoming zero.

Details reuse the overlay's downloaded batch without another API request. City
playback pauses on selection; radar playback is independent. Changing the city
time controls or refreshing updates the selected city's details. Close dismisses
selection. Hiding Navigation, disabling the overlay, or changing the viewport's
city set closes details and rejects obsolete selections.

`CityWeatherOverlayState.details` carries immutable SI summary/hourly values.
`WeatherOverlayRequestHandlerIf.request_city_details` handles selection and
closure. The native map returns a `weather-city:` identity in `map.click` only
when hit testing finds a rendered weather feature; POI selection ignores those
hits. The weather adapter consumes them independently of city-query replies.
City identities include coordinates to distinguish places with the same name.

Clickable city weather requires rebuilding the native map renderer after pulling
this change; Python-only updates cannot add native feature hit testing. On
Termux the existing `development/termux/build_navigation_stack.sh` rebuilds the
ORC renderer while reusing unchanged native dependencies.
