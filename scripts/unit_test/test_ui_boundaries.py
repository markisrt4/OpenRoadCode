# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Architecture gate rejects new dependencies and cannot silently grow exceptions."""
from scripts.check_ui_boundaries import check, violations


def test_new_nested_frontend_is_discovered(tmp_path):
    path = tmp_path / 'apps/newApp/frontend/widgets/new_view.py'
    path.parent.mkdir(parents=True)
    path.write_text('import requests as http\n')
    paths, errors = check(tmp_path, {})
    assert path in paths
    assert errors and 'requests' in errors[0]


def test_alias_member_relative_and_domain_imports_are_checked():
    for path, source in (
        ('frontends/tk/view.py', 'from urllib import request as http'),
        ('frontends/tk/view.py', 'from controllers.weather import WeatherController'),
        ('controllers/weather/worker.py', 'from ...frontends.tk import view'),
        ('ui/weather/state.py', 'import controllers.weather as backend'),
    ):
        assert violations(path, source)
    assert not violations('frontends/tk/view.py', 'from ui.weather import WeatherUiIf')


def test_exception_only_allows_exact_existing_dependency_and_count(tmp_path):
    path = tmp_path / 'frontends/tk/view.py'
    path.parent.mkdir(parents=True)
    path.write_text('from controllers.weather import WeatherController\n')
    key = 'frontends/tk/view.py|imports controllers.weather.WeatherController'
    baseline = {key: {'count': 1, 'reason': 'Existing controller coupling'}}
    assert not check(tmp_path, baseline)[1]
    path.write_text('from controllers.weather import WeatherController, WeatherPresenter\n')
    assert check(tmp_path, baseline)[1]
    path.write_text('from controllers.weather import WeatherController\n' * 2)
    assert check(tmp_path, baseline)[1]
    path.write_text('from ui.weather import WeatherUiIf\n')
    assert 'stale' in check(tmp_path, baseline)[1][0]


def test_existing_repository_matches_explicit_baseline():
    import json
    from scripts.check_ui_boundaries import ROOT, BASELINE
    assert not check(ROOT, json.loads(BASELINE.read_text()))[1]


def test_contracts_cannot_depend_on_other_repository_packages():
    for module in ('common.units', 'messaging.contracts', 'config.runtime_environment'):
        assert violations('ui/new_feature/state.py', f'import {module}')
    assert not violations('ui/theme/style_sheet.py', 'import tinycss2')
