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


def test_automotive_frontends_cannot_reintroduce_application_theme_dependencies():
    for source in (
        'from apps.common.uiTheme import VehicleGaugeTheme as Theme',
        'from apps.common.uiTheme.vehicle_gauges import VEHICLE_GAUGE_THEME',
        'import apps.common.uiTheme as application_theme',
        'import apps',
        'from ....apps.common import uiTheme',
    ):
        assert violations('frontends/tk/automotive/new_gauge.py', source)
    assert not violations('frontends/tk/automotive/new_gauge.py',
                          'from ui.theme import VehicleGaugeTheme')


def test_new_automotive_widget_with_app_dependency_fails_gate(tmp_path):
    path = tmp_path / 'frontends/tk/automotive/nested/gauge.py'
    path.parent.mkdir(parents=True)
    path.write_text('from apps.custom_dashboard import theme\n')
    paths, errors = check(tmp_path, {})
    assert path in paths
    assert errors and 'apps.custom_dashboard.theme' in errors[0]


def test_frontend_cannot_hide_backend_imports_in_core_runtime_module():
    assert violations('apps/orcUi/frontend/tk/navigation_screen.py',
                      'from apps.orcUi.core_runtime import MapRuntimeIf')
    assert not violations('apps/orcUi/frontend/tk/navigation_screen.py',
                          'from ui.navigation.map_runtime_if import MapRuntimeIf')


def write_source(root, relative, source):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return path


def test_marked_widget_outside_frontend_directories_cannot_import_backend(tmp_path):
    path = write_source(tmp_path, 'plugins/dashboard/panel.py',
                        'from ui.ui_widget import UiWidget as Policy\n'
                        'from services.navigation import Client\n'
                        'class Panel(Policy): pass\n')
    paths, errors = check(tmp_path, {})
    assert path in paths
    assert any('services.navigation.Client' in error for error in errors)


def test_transitive_widget_policy_survives_relative_imports_and_reexports(tmp_path):
    write_source(tmp_path, 'plugins/dashboard/base.py',
                 'import ui.ui_widget as policy\n'
                 'class Base(policy.UiWidget): pass\n')
    write_source(tmp_path, 'plugins/dashboard/__init__.py',
                 'from .base import Base as Exported\n')
    write_source(tmp_path, 'plugins/dashboard/intermediate.py',
                 'from . import Exported\n'
                 'class Middle(Exported): pass\n')
    path = write_source(tmp_path, 'plugins/dashboard/panel.py',
                        'from .intermediate import Middle as Parent\n'
                        'import apps.orcUi.composition.core\n'
                        'class Panel(Parent): pass\n')
    paths, errors = check(tmp_path, {})
    assert path in paths
    assert any('apps.orcUi.composition.core' in error for error in errors)


def test_marker_public_export_accepts_toolkit_rendering_and_contracts(tmp_path):
    path = write_source(tmp_path, 'plugins/dashboard/panel.py',
                        'from ui import UiWidget\n'
                        'import tkinter as tk\n'
                        'from ui.weather import WeatherRequestHandlerIf\n'
                        'class Panel(tk.Frame, UiWidget): pass\n')
    paths, errors = check(tmp_path, {})
    assert path in paths
    assert not errors


def test_unrelated_class_with_same_name_does_not_mark_backend(tmp_path):
    path = write_source(tmp_path, 'plugins/backend.py',
                        'import requests\n'
                        'class UiWidget: pass\n'
                        'class Client(UiWidget): pass\n')
    paths, errors = check(tmp_path, {})
    assert path not in paths
    assert not errors


def test_importing_marker_without_inheriting_does_not_mark_composition(tmp_path):
    path = write_source(tmp_path, 'plugins/composition.py',
                        'from ui import UiWidget\n'
                        'import services.navigation\n'
                        'def bind(widget: UiWidget): pass\n')
    paths, errors = check(tmp_path, {})
    assert path not in paths
    assert not errors


def test_marked_widget_worker_and_transport_imports_fail_even_inside_methods(tmp_path):
    path = write_source(tmp_path, 'plugins/dashboard/panel.py',
                        'from ui import UiWidget\n'
                        'class Panel(UiWidget):\n'
                        '    def refresh(self):\n'
                        '        import threading\n'
                        '        from protocols import transport\n')
    paths, errors = check(tmp_path, {})
    assert path in paths
    assert any('threading' in error for error in errors)
    assert any('protocols.transport' in error for error in errors)


def test_games_cannot_reintroduce_application_or_native_adapter_dependencies():
    for dependency in ('apps.games', 'frontends.x11.x11_window_embedder'):
        errors = violations('frontends/tk/games/new_panel.py', f'import {dependency}\n')
        assert errors


def test_radio_presentation_cannot_import_application_services():
    assert violations('frontends/tk/radio/new_panel.py', 'import apps.orcUi.radio_application_service\n')


def test_streaming_frontends_have_no_legacy_backend_exceptions():
    import json
    from pathlib import Path
    baseline = json.loads((Path(__file__).resolve().parents[1] / 'ui_boundary_exceptions.json').read_text())
    prefixes = (
        'frontends/tk/radio/streaming_radio_panel.py|',
        'frontends/tk/radio/persistent_streaming_radio_panel.py|',
        'frontends/tk/radio/streaming_radio_now_playing.py|',
    )
    assert not any(key.startswith(prefixes) for key in baseline)
