# Computing-unit performance

OpenRoadCode samples the host computing unit once per second and keeps 120
samples in memory. The sampler works on Linux, including Raspberry Pi and
Termux where the operating system permits access to host statistics. Missing
or restricted measurements remain unavailable; they are not reported as zero.

## View the standalone screen

From an updated OpenRoadCode checkout on a graphical desktop, use the same
Python environment as ORC:

```bash
cd OpenRoadCode
venv/bin/python -m frontends.tk.system.component_test.performance_preview
```

Use `python` instead of `venv/bin/python` if ORC's dependencies are installed
in that interpreter. The screen profiles the machine running the command.
It does not need the map renderer, automotive services, or a running ORC shell.

The integrated ORC screen is registered as `DIAGNOSTICS`, with no navigation
shortcut. Its placement is intentionally undecided. Runtime composition can
open it through `app.navigate_to("DIAGNOSTICS")` when an entry point is chosen.

## View from Android Bridge

Both OpenRoadCode and Android Bridge need the performance changes installed.
The existing released APK does not contain the new card.

On a Linux computing unit, rerun the service-manager installer from the updated
checkout. The service manager runs from its installed copy, so restarting the
old installed service alone does not copy new source files:

```bash
sudo scripts/systemd/install_service_manager_systemd.sh
```

The installer preserves the existing administrative token and pairing store.
On Termux, update the checkout and restart `openroadcode-service-manager` with
the existing runit service controls.

Build and install the updated Android Bridge app using that repository's build
instructions. Pair or select the computing unit under **Configuration**, then
open **Runtime**, select the remote runtime target, and expand **Computing Unit
Performance**. Selecting Termux displays the local Termux runtime instead.
The remote card uses the saved pairing credential and service-manager endpoint;
there is no additional port or pairing flow. Polling stops when the Runtime
screen is left or the app is paused. Switching target discards the previous
unit's readings. Connection failures or samples older than three seconds are
displayed as unavailable.

## Measurements and limits

- CPU utilization uses deltas from `/proc/stat`, including individual cores.
  Guest time is not counted twice. The first sample has no utilization value.
- Frequency is the average of available per-core `scaling_cur_freq` readings.
  Load is the host's one-minute load average.
- RAM utilization is `MemTotal - MemAvailable`; swap uses `SwapTotal - SwapFree`.
- Storage capacity is measured for `/`. Disk activity sums whole physical
  block-device sector counters, excluding partitions and stacked virtual disks.
  Kernel diskstat sectors are 512 bytes.
- Network activity sums interface byte counters except loopback. Virtual
  interfaces may count the same traffic as their underlying interfaces.
- Temperature is the hottest available thermal-zone reading. Headroom uses
  the lowest available passive/hot/critical thermal trip point. Pi models fall
  back to 85°C when no trip point is exposed. Other models have no assumed
  limit. These host-level thermal figures are a broad health indicator, not
  an individual CPU's guaranteed throttling threshold.
- Pi firmware throttling flags come from `vcgencmd get_throttled`, with a
  250 ms timeout. Other hosts normally show this as unavailable. A restricted
  systemd service may not be allowed to read firmware flags.
- Uptime comes from `/proc/uptime`. I/O rates use monotonic elapsed time and
  suppress first samples, reset counters, and newly attached devices.

These are host resource measurements, not function-level tracing, frame-time
profiling, or process-specific CPU accounting. History is bounded and is lost
when the sampler process restarts.

## HTTP contract

`GET /performance` is served by the existing service manager on port 8769,
after the same authentication used by `/services`. Remote callers need a
valid administrative or paired-client bearer credential. The existing Termux
loopback policy still applies.

Version 1 returns `version`, `sample_interval_seconds`, `sample_age_seconds`,
`error`, `snapshot`, and `history`. Before the first sample, `snapshot` and
`sample_age_seconds` are null and `history` is empty. A sampler failure retains
the previous snapshot with an increasing age and an error type; clients must
check freshness before displaying it as live.

The snapshot includes host identity, Unix sample time, CPU utilization and
per-core percentages, load, CPU count, frequency in Hz, memory/swap/disk byte
counts, utilization percentages, temperatures in Celsius, uptime in seconds,
Pi throttle flags, and network/disk rates in bytes per second. History contains
only sample time, CPU percentage, memory percentage, and temperature to keep
remote responses compact. Unavailable values are JSON null. Responses use
`Cache-Control: no-store`.
