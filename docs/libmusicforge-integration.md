# libMusicForge audio-analysis integration

OpenRoadCode delegates OpenRoadCode's FFT analyzer, analysis interface, and
analysis state models to the reusable `musicforge.analysis` package.

## Development setup

Install libMusicForge in the **same Python environment** used to run OpenRoadCode.
With both repositories checked out as siblings:

```bash
cd ../libMusicForge
python -m pip install -e '.[analysis]'
cd ../OpenRoadCode
```

On Termux, NumPy may need to be installed using `pkg install python-numpy`
rather than built with pip. Create the venv with `--system-site-packages`
and install libMusicForge using `python -m pip install -e ../libMusicForge --no-deps`
if NumPy is already supplied by Termux.

## Migration boundary

The following legacy imports remain supported by lightweight compatibility
modules, and now resolve to libMusicForge implementations:

- `controllers.audio.music_analysis.music_analyzer.MusicAnalyzer`
- `controllers.audio.music_analysis.music_analyzer_if.MusicAnalyzerIf`
- `controllers.audio.music_analysis.music_analysis_types.MusicAnalysisState`
- `controllers.audio.music_analysis.music_analysis_types.PercussionActivity`

Existing `controllers.audio.music_analysis` package-level imports remain
available. Capture backends, pipeline, session lifecycle, fanout, and
visualization stay in OpenRoadCode.

## Verification

```bash
python -c 'from controllers.audio.music_analysis import MusicAnalyzer; print(MusicAnalyzer.__module__)'
python -m pytest -q controllers/audio/music_analysis/unit_test
python -m pytest -q controllers/audio/music_analysis/component_test
```

The first command should print `musicforge.analysis.analyzer`. Test results
must be verified locally; the branch changes were not executed on the target
device. No dependency is vendored into OpenRoadCode; installation is required
before importing the analysis modules.

The source analyzer was MIT licensed. Its original implementation and
copyright/license notices are retained in libMusicForge.

## Installer behavior

Both `scripts/installers/install_python_env.sh` and `scripts/termux/install.sh`
invoke `scripts/installers/install_libmusicforge.sh` in the selected virtual
environment. By default the helper prefers a sibling `../libMusicForge`
checkout only when its metadata declares the analysis extra and its source tree
contains `musicforge.analysis`. Otherwise it installs a verified GitHub revision
(`7ca7cd444291ab02bea0e82df13bd05620634420`). Set `LIBMUSICFORGE_SOURCE`
to override that source. On Termux, `python-numpy` must be visible inside
the virtual environment; the helper avoids compiling NumPy with pip.
The Termux environment check verifies that the shared analyzer imports.

For local development, install the sibling library in editable mode:

```bash
python -m pip install -e ../libMusicForge --no-deps  # Termux, with python-numpy installed
```

A normal installer run uses a non-editable installation and explicitly replaces
the existing package, even when both old and current revisions report version
`0.1.0`. Subsequent library changes require reinstalling it. Explicit incompatible
local overrides are rejected before pip runs; sibling checkouts are not modified. The core libMusicForge wheel excludes its
standalone `component_test/` examples, which are run from its source checkout.

## Native visualizer checks

From the OpenRoadCode root with an X11 display:

```bash
python -m apps.orcUi.component_test.native_music_visualizer_cli
python -m apps.orcUi.component_test.home_music_visualizer_cli
```

These use synthetic analysis/capture and do not validate Android playback
permissions or hardware GPU compatibility. See `docs/music_visualizer.md`
for device-specific checks.


## Startup dependency check

Normal `./runOrcUi` startup checks that the required `musicforge.analysis` analyzer,
interface and state types import before loading application composition. A missing
package, missing analysis dependency, or incompatible analysis API produces a
short setup message and exit code 2, rather than the composition traceback. Help
and ECU renderer diagnostics remain available independently of the audio library.
No packages are installed automatically during UI startup.

The recovery message names the exact selected Python interpreter. The existing
installer accepts `PYTHON` so a repair targets the same interpreter even if a
different environment is activated. For a Linux checkout using `venv`:

```bash
git switch navigation-cesium
source venv/bin/activate
PYTHON="$VIRTUAL_ENV/bin/python" bash scripts/installers/install_libmusicforge.sh
./runOrcUi
```

On Termux, activate `venv-termux` instead; the existing system NumPy policy in the
installer still applies.
