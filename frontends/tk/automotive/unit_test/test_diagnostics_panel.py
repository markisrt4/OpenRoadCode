# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Render and lifecycle checks; run with an X display, skip on headless hosts."""
import tkinter as tk
from dataclasses import replace
from unittest.mock import Mock

import pytest

from apps.orcUi.theme_runtime import theme_bundle
from controllers.automotive.diagnostics_scan_controller import present_diagnostics
from frontends.tk.automotive.diagnostics_panel import VehicleDiagnosticsPanel
from ui.automotive.diagnostics_scan_if import DiagnosticsScanState
from ui.theme import ThemeMode


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f'X display required: {error}')
    errors = []
    window.report_callback_exception = lambda *error: errors.append(error)
    window.geometry('800x480')
    yield window
    window.destroy()
    assert not errors


def fault_state():
    return present_diagnostics(dict(mil_on=True, emissions_ready=True, stored_dtc_count=1,
        responding_ecus=[0x7E8], completed_services=['monitor', 'stored', 'pending', 'permanent'],
        trouble_codes=[dict(code='P0300', status='stored', ecu_id=0x7E8)]))


def visible_text(widget):
    values = [str(widget.cget('text'))] if isinstance(widget, (tk.Label, tk.Button)) else []
    for child in widget.winfo_children():
        values.append(visible_text(child))
    return '\n'.join(values)


def test_fault_meaning_visible_identifiers_expand_and_refresh(root):
    panel = VehicleDiagnosticsPanel(root, theme=theme_bundle(ThemeMode.DARK), handler=Mock())
    panel.pack(fill=tk.BOTH, expand=True)
    panel.update_diagnostics(fault_state())
    root.update()
    assert 'Engine misfire' in visible_text(panel)
    assert 'P0300' not in visible_text(panel)
    assert '0x7E8' not in visible_text(panel)
    panel._details_button.invoke()
    root.update()
    assert 'P0300' in visible_text(panel)
    assert '0x7E8' in visible_text(panel)
    panel.update_diagnostics(DiagnosticsScanState(summary='Diagnostics unavailable'))
    root.update()
    assert 'P0300' not in visible_text(panel)
    assert 'Engine misfire' not in visible_text(panel)
    assert 'Diagnostics unavailable' in visible_text(panel)
    assert panel._expanded


def test_scan_progress_and_busy_cleanup(root):
    handler = Mock()
    panel = VehicleDiagnosticsPanel(root, theme=theme_bundle(ThemeMode.DARK), handler=handler)
    panel.pack(fill=tk.BOTH, expand=True)
    panel._scan.invoke()
    handler.request_scan.assert_called_once()
    panel.update_diagnostics(DiagnosticsScanState(scanning=True, status='scanning', summary='Scanning…'))
    root.update()
    assert str(panel._scan.cget('state')) == tk.DISABLED
    assert panel._progress.winfo_ismapped()
    panel._scan.invoke()
    handler.request_scan.assert_called_once()
    panel.update_diagnostics(fault_state())
    root.update()
    assert str(panel._scan.cget('state')) == tk.NORMAL
    assert not panel._progress.winfo_ismapped()
    assert 'Scan finished' in panel._timestamp.cget('text')
    panel.update_diagnostics(replace(fault_state(), scanning=True))
    root.update()
    panel.destroy()  # Stop the progress timer before destroying child widgets.
    root.update()


def test_multiple_faults_and_technical_details_remain_scrollable(root):
    panel = VehicleDiagnosticsPanel(root, theme=theme_bundle(ThemeMode.DARK), handler=Mock())
    panel.pack(fill=tk.BOTH, expand=True)
    state = fault_state()
    panel.update_diagnostics(replace(state, faults=state.faults * 6))
    root.update()
    panel._canvas.yview_moveto(1)
    root.update()
    assert panel._canvas.yview()[0] > 0
    assert panel._canvas.yview()[1] == 1
    panel._details_button.invoke()
    root.update()
    assert 'P0300' in visible_text(panel)
