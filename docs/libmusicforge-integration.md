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
checkout and otherwise installs from GitHub. Set `LIBMUSICFORGE_SOURCE`
to override that source. On Termux, `python-numpy` must be visible inside
the virtual environment; the helper avoids compiling NumPy with pip.
The Termux environment check verifies that the shared analyzer imports.

For local development, install the sibling library in editable mode:

```bash
python -m pip install -e ../libMusicForge --no-deps  # Termux, with python-numpy installed
```

A normal installer run uses a non-editable installation, so subsequent library
changes require reinstalling it. The core libMusicForge wheel excludes its
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
