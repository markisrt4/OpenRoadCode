# libMusicForge audio-analysis integration

This branch delegates OpenRoadCode's FFT analyzer, analysis interface, and
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
