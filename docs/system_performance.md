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

## View inside ORC

Run ORC normally with `python -m apps.orcUi` (or `venv/bin/python -m apps.orcUi`
when using its virtual environment). Tap the small **● SYS** indicator at the
persistent control row beside Settings and the theme control to open Diagnostics on **ORC workload**.
The indicator remains available on every screen. **Back** returns to the
navigation destination that opened Diagnostics. No sidebar entry is added.

The label accompanies its color: **OK** is green for normal observed readings;
**CPU**, **RAM**, **DISK**, **THERMAL**, **SENSOR**, or **SERVICE** identify the most severe
current condition in amber or red. **PART** means restricted process visibility;
**—** means waiting or unavailable measurements; **OLD** means the cached sample
has stopped advancing for over three seconds. These unknown states are muted.
Green summarizes available resource readings and observed sensor streams; it
is not a hardware self-test and does not certify unobserved or disabled sensors.

The indicator reads the same background sampler cache once per second; it does
not scan processes or query firmware on the Tk thread. Theme changes retain its
state, and application shutdown cancels the UI refresh loop.

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
On Termux, update the main OpenRoadCode checkout and restart the Python service
manager. Updating the Bridge APK alone does not update this process:

```bash
cd ~/src/OpenRoadCode
git fetch origin computing-unit-performance
git switch computing-unit-performance
git merge --ff-only FETCH_HEAD
sv restart openroadcode-service-manager
```

A 404 from `/performance` means the running server does not expose this route.
If restarting still returns 404, reinstall the runit definitions from this checkout
with `bash scripts/runit/install_termux_services.sh` and restart again, so the
service uses the correct source directory.

Build and install the updated Android Bridge app using that repository's build
instructions. Pair or select the computing unit under **Configuration**, then
open **Performance** from the Bridge subsystem dashboard, use **Computing unit**
to select the remote unit, and view **Computing Unit Performance**. Selecting
Local Termux displays the local Termux runtime instead. Runtime contains service
settings and lifecycle controls, not metrics.
The remote card uses the saved pairing credential and service-manager endpoint;
there is no additional port or pairing flow. Polling stops when the Performance
screen is left or the app is paused. Switching target discards the previous
unit's readings. Connection failures or samples older than three seconds are
displayed as unavailable.

## ORC workload attribution

The preview opens on **ORC workload**. It shows combined CPU use and a table of
processes sorted by CPU use, with PID, CPU percentage, resident memory (RSS),
proportional memory (PSS), thread count, and actual disk read/write byte rates.
The other tabs are **System**, **Sensor telemetry**, and **Services**. The persistent **● SYS**
indicator opens this screen inside ORC.

Recognized roots include the ORC UI/application modules, navigation, automotive,
Android sensor, weather and trip services, the message broker, and native
`openroadcode-map-renderer`, `sdrpp`, and `readsb` integration processes.
Descendants are attributed using process parentage, including renderer/browser
helpers. A known child remains attributed after reparenting until it exits.
Arbitrary Python processes and commands merely mentioning ORC are excluded.
Native integrations are included by executable identity; this identifies their
resource cost, not exclusive ownership by ORC.

CPU uses each process's own user/system tick deltas, including its threads but
not cumulative child CPU. PID plus kernel start time prevents PID reuse from
creating spikes. 100% is one fully occupied logical core. The normalized CPU
capacity percentage divides the sum by the reported logical core count; it is
an estimate of capacity use, not a percentage of the host's currently busy CPU.
First observations and counter resets are unavailable until the next sample.
The scanner measures visible live processes; short-lived processes that exit
between samples may be missed.

Dedicated preview and service-manager processes are labelled **diagnostics**
and excluded from the workload total. Their own resource usage remains visible
in the table. Sampling performed inside the ORC UI is part of that UI's process.

RSS sums count shared pages once for each process mapping them. They are useful
for per-process residency, but should not be interpreted as unique physical
memory consumed by ORC. PSS apportions shared pages and is the better aggregate
footprint estimate. PSS and disk I/O counters may be restricted by Android or by
user permissions. Totals remain unavailable when an included process lacks a
required metric, rather than silently treating it as zero. Partial discovery
is explicitly labelled. A kernel that hides entire PID directories cannot
report that hidden population to this scanner.

## Sensor telemetry health

The monitor subscribes to the existing local message broker; it never opens or
competes for a sensor. It tracks GPS position, IMU, magnetometer, derived
attitude, ambient light, and barometer streams, separately for each source.
Each row shows state, time since receipt, time since the sample timestamp last
advanced, recent valid-message rate, and cumulative invalid-message count.
Select a stream for its detail and stale threshold.

- **Streaming** means valid messages with advancing timestamps are arriving.
- **Stale** means messages stopped or the sample timestamp stopped advancing.
- **Degraded** GPS means no usable fix or a cached position.
- **Invalid** means the latest message failed its public contract validator.
- **Not observed** is unknown: the input may be disabled or unconfigured.

Receipt and timestamp-advancement ages use the observer's monotonic clock,
so remote wall-clock skew does not automatically make a sensor stale. Rates
use up to the last five seconds of valid receipts. Histories and source counts
are bounded. Default stale thresholds are GPS/barometer 10 seconds, IMU 3,
magnetometer/attitude 5, and ambient light 30. Event-driven sensors can be quiet
without being broken; these thresholds are telemetry policies, not self-tests.
A producer that timestamps republished cached values as new cannot be diagnosed
as a physical sampling failure from freshness alone.

The sensor monitor requires `pyzmq` in the interpreter running the preview or
service manager, plus a running broker and producers. Other performance
measurements work without it, and the screen reports the missing transport.
For a Linux service manager using system Python on Debian/Ubuntu, install
`python3-zmq` (for example, `sudo apt install python3-zmq`), then rerun the
service-manager installer from the updated checkout. Termux should use ORC's
existing Python environment with `pyzmq` installed.

## Measurements and limits

- CPU utilization uses deltas from `/proc/stat`, including individual cores.
  Guest time is not counted twice. The first sample has no utilization value.
  This is the percentage of non-idle CPU time across the host cores; iowait
  is excluded. Modern Android commonly denies Termux access to `/proc/stat`,
  so host CPU and per-core percentages can remain unavailable. The screen
  explains this restriction instead of displaying a fabricated percentage.
- **This process CPU** uses Python's monotonic process CPU clock across all
  threads, divided by elapsed wall time. 100% means one fully occupied core;
  values may exceed 100% with multiple busy threads. It measures only the
  sampling process (the preview, ORC UI, or service manager), not the entire
  phone, all Termux processes, or every ORC service. It is shown separately
  and is never substituted for the unavailable host reading.
- Frequency is the average of available per-core `scaling_cur_freq` readings.
  Load is the host's one-minute load average.
- RAM utilization is `MemTotal - MemAvailable`; swap uses `SwapTotal - SwapFree`.
- Storage capacity is measured for `/` on Linux and Termux's home/data
  filesystem on Android. The sampled path is included in the snapshot. Used
  space comes from filesystem-used blocks, not total minus space available
  to an unprivileged user (which would count reserved free space as used).
  Disk activity sums whole physical
  block-device sector counters, excluding partitions and stacked virtual disks.
  Kernel diskstat sectors are 512 bytes.
- Network activity sums interface byte counters except loopback. Virtual
  interfaces may count the same traffic as their underlying interfaces.
- Temperature is the hottest available thermal-zone reading. Headroom uses
  the lowest available passive/hot/critical trip point of that same thermal
  zone; it never mixes thresholds from another sensor. The screen calls this
  distance **to trip**, rather than implying a guaranteed CPU throttling
  threshold. Pi models fall
  back to 85°C when no trip point is exposed. Other models have no assumed
  limit. These host-level thermal figures are a broad health indicator, not
  an individual CPU's guaranteed throttling threshold.
- Pi firmware throttling flags come from `vcgencmd get_throttled`, with a
  250 ms timeout. Other hosts normally show this as unavailable. A restricted
  systemd service may not be allowed to read firmware flags.
- Uptime comes from `/proc/uptime`. I/O rates use monotonic elapsed time and
  suppress first samples, reset counters, and newly attached devices.

Host counters and per-process accounting do not provide function-level traces
or rendering/frame-time profiles. History is bounded and is lost
when the sampler process restarts.

## HTTP contract

`GET /performance` is served by the existing service manager on port 8769,
after the same authentication used by `/services`. Remote callers need a
valid administrative or paired-client bearer credential. The existing Termux
loopback policy still applies.

The additions preserve Version 1 compatibility. `snapshot.workload` contains
visible per-process rows, aggregate workload totals, and visibility detail.
`snapshot.sensors` contains per-topic/source telemetry-health rows and
`snapshot.sensor_monitor_status` describes receiver availability. No command
lines or process environments are exported.

Version 1 returns `version`, `sample_interval_seconds`, `sample_age_seconds`,
`error`, `snapshot`, and `history`. Before the first sample, `snapshot` and
`sample_age_seconds` are null and `history` is empty. A sampler failure retains
the previous snapshot with an increasing age and an error type; clients must
check freshness before displaying it as live.

The snapshot includes host identity, Unix sample time, CPU utilization and
per-core percentages, a host CPU unavailability reason, sampler-process CPU
percentage and PID, load, CPU count, frequency in Hz, memory/swap/disk byte
counts, utilization percentages, temperatures in Celsius, uptime in seconds,
Pi throttle flags, storage path, thermal zone, and network/disk rates in bytes
per second. History contains
only sample time, host/process/ORC CPU percentages, aggregate ORC RSS bytes,
host memory percentage, and temperature to keep
remote responses compact. Unavailable values are JSON null. Responses use
`Cache-Control: no-store`.

### Status colors

Sensor telemetry uses green for streaming, amber for stale or degraded, red for invalid,
and muted text for unknown or unobserved streams. State labels remain visible.
CPU capacity, RAM and storage turn amber at 80% and red at 95%; these indicate
resource pressure, not a process failure. Thermal readings turn amber within 10°C
of the reported trip point and red within 5°C. Unknown readings stay neutral.
ORC workload is blue, diagnostics processes are muted, and trends use distinct colors.
CPU totals include all threads: 200% on eight logical CPUs is 25% of capacity.
Capacity uses the detected logical CPU count; it does not adjust for CPU affinity,
container quotas, or differing performance between CPU types.

## Services and TCP/UDP traffic

The fourth Diagnostics tab, **Services**, lists TCP/UDP endpoints owned by visible
ORC processes and integrations, including the broker, navigation, automotive,
Android sensor service, trip/weather services, service manager, GPSD, ADS-B,
SDR++ and the map renderer. Discovered ORC descendants are included. Optional
integrations with no visible process are **NOT_OBSERVED**, not assumed failed.
This is local computing-unit socket observation; services running on another
machine appear through their visible client connections, not remote PID discovery.

Each endpoint shows PID, protocol, local/peer address, socket state, receive/transmit
payload KiB/s, receive/transmit queue occupancy in bytes, and UDP drop count.
TCP **LISTENING** and **CONNECTED** are green observed transport states; neither
is a successful application health probe. UDP **BOUND** is blue and does not
prove delivery. Current UDP drops and stopped/zombie owners are red. Selecting
a row shows the measurement detail and current UDP drops per second. The Android
Bridge performance card presents the same cached service/socket data.

TCP rates use differences in kernel TCP_INFO `bytes_received` and `bytes_sent`,
read with `ss` from iproute2. They measure TCP payload, exclude packet headers,
and sent bytes include retransmissions. First samples, missing counters, reset
counters, and another network namespace have unavailable rates. Listeners may
not have byte counters; rates belong to their connected sockets. Connections
that open and close entirely between samples are missed. Shared socket owners
may each show the same endpoint; rows must not be summed as unique network traffic.

Linux procfs exposes UDP queues and drops but no per-socket byte counters. UDP
RX/TX bandwidth therefore stays **--**; queue occupancy is never used as a byte
rate. Per-service UDP bandwidth needs counters supplied by that service or
privileged packet accounting. Restricted Android/Termux socket tables and FD
ownership also stay unavailable. No root privileges, active TCP/UDP probes,
service starts/stops, or packet capture are requested by this monitor.

At most 256 endpoint rows are retained per sample, with an explicit truncation
notice. `ss` has a half-second timeout and runs only on the existing background
sampler; the UI and HTTP endpoint read cached data. To enable supported TCP
byte counters on Linux, install iproute2 (`sudo apt install iproute2`). On Termux,
`pkg install iproute2` may supply `ss`, but Android permissions can still prevent
access. Rerun the Linux service-manager installer to update its installed copy.
