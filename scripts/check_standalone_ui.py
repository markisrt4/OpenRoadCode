#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Prove every contract imports with only ui/ available and exercise a replacement UI."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROBE = '''
import importlib
import importlib.abc
import pkgutil
import sys

class NoBackendImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'apps', 'controllers', 'services', 'protocols',
                                      'hardware_io', 'messaging', 'config', 'common', 'frontends'}:
            raise ImportError(f'Contract package attempted backend import: {fullname}')
sys.meta_path.insert(0, NoBackendImports())
import ui
modules = [entry.name for entry in pkgutil.walk_packages(ui.__path__, 'ui.')]
for module in modules:
    importlib.import_module(module)

from ui.weather import WeatherUiIf, WeatherUiState, WeatherCurrentUiState
from ui.weather.weather_request_handler_if import WeatherRequestHandlerIf
class ReplacementWeatherView(WeatherUiIf):
    def set_weather_state(self, state):
        self.state = state
    def set_weather_request_handler(self, handler):
        self.handler = handler
class FakeBackend(WeatherRequestHandlerIf):
    def __init__(self, view):
        self.view = view
    def request_refresh(self):
        self.view.set_weather_state(WeatherUiState(
            location_name='Contract demo',
            current=WeatherCurrentUiState(temperature_k=293.15)))
view = ReplacementWeatherView()
view.set_weather_request_handler(FakeBackend(view))
view.handler.request_refresh()
assert view.state.current.temperature_k == 293.15
assert view.state.location_name == 'Contract demo'
assert not any(name.split('.')[0] in {'apps', 'controllers', 'services', 'protocols'}
               for name in sys.modules)
print(f'Imported {len(modules)} standalone contract modules; replacement UI request/state round trip passed.')
'''


def main():
    with tempfile.TemporaryDirectory(prefix='openroad-ui-contracts-') as directory:
        target = Path(directory)
        shutil.copytree(ROOT / 'ui', target / 'ui', ignore=shutil.ignore_patterns(
            '__pycache__', 'unit_test', 'component_test'))
        (target / 'probe.py').write_text(PROBE)
        # Isolated interpreter ignores PYTHONPATH and the current repository.
        wrapper = f"import sys; sys.path.insert(0, {str(target)!r}); exec(open({str(target / 'probe.py')!r}).read())"
        return subprocess.run([sys.executable, '-I', '-c', wrapper], cwd=target, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
