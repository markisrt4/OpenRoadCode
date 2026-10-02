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
