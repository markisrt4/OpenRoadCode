# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import threading
import unittest
from controllers.automotive.diagnostics_scan_controller import DiagnosticsScanController, present_diagnostics

class _Dispatcher:
    def __init__(self):
        self.callbacks = []
        self.ready = threading.Event()
    def dispatch_ui(self, callback):
        self.callbacks.append(callback)
        self.ready.set()

class DiagnosticsPresentationTest(unittest.TestCase):
    def healthy(self):
        return dict(mil_on=False, emissions_ready=True, stored_dtc_count=0,
                    trouble_codes=[], responding_ecus=[0x7E8],
                    completed_services=['monitor', 'stored', 'pending', 'permanent'])

    def test_incomplete_and_no_ecu_never_present_healthy(self):
        for patch in [dict(completed_services=[]), dict(responding_ecus=[]), dict(mil_on=None), dict(emissions_ready=None)]:
            self.assertEqual(present_diagnostics(self.healthy() | patch).status, 'unavailable')
        self.assertEqual(present_diagnostics(self.healthy()).status, 'healthy')
        state = present_diagnostics(self.healthy() | dict(emissions_ready=False))
        self.assertNotEqual(state.status, 'healthy')
        self.assertIn('not ready', state.summary)

    def test_pending_and_permanent_are_faults_without_mil(self):
        for status in ['pending', 'permanent']:
            state = present_diagnostics(self.healthy() | dict(trouble_codes=[dict(code='P0300', status=status, ecu_id=0x7E8)]))
            self.assertEqual(state.status, 'faulted')
            self.assertIn('misfire', state.details)
            self.assertIn('MIL / Check Engine: OFF', state.details)

    def test_worker_dispatch_hide_and_close_discard_stale_callbacks(self):
        dispatcher = _Dispatcher()
        release = threading.Event()
        calls = []
        def scan():
            calls.append(1)
            release.wait(1)
            return self.healthy()
        controller = DiagnosticsScanController(scan, dispatcher)
        states = []
        remove = controller.observe(states.append)
        controller.request_scan()
        controller.request_scan()
        self.assertTrue(states[-1].scanning)
        remove()  # Screen hidden; completion must not call destroyed widgets.
        count = len(states)
        release.set()
        self.assertTrue(dispatcher.ready.wait(1))
        dispatcher.callbacks.pop()()
        self.assertEqual(len(states), count)
        remount = []
        controller.observe(remount.append)
        self.assertEqual(remount[-1].status, 'healthy')
        self.assertEqual(len(calls), 1)
        dispatcher.ready.clear()
        controller.request_scan()
        self.assertTrue(dispatcher.ready.wait(1))
        controller.close()
        for callback in dispatcher.callbacks:
            callback()
        self.assertTrue(controller._closed)

    def test_worker_failure_reports_unavailable(self):
        dispatcher = _Dispatcher()
        def fail():
            raise TimeoutError('scan timed out')
        controller = DiagnosticsScanController(fail, dispatcher)
        states = []
        controller.observe(states.append)
        controller.request_scan()
        self.assertTrue(dispatcher.ready.wait(1))
        dispatcher.callbacks.pop()()
        self.assertEqual(states[-1].status, 'unavailable')
        self.assertIn('timed out', states[-1].details)

    def test_plain_language_fault_cards_keep_identifiers_in_technical_details(self):
        from datetime import datetime, timezone
        finished = datetime(2026, 11, 4, 12, 30, tzinfo=timezone.utc)
        titles = {
            'P0300': 'Engine misfire', 'P0171': 'Lean fuel mixture',
            'P0420': 'Reduced exhaust cleaning', 'P0455': 'Fuel-vapor system leak',
            'P1234': 'Vehicle-reported fault',
        }
        for code, title in titles.items():
            state = present_diagnostics(self.healthy() | dict(
                mil_on=True, trouble_codes=[dict(code=code, status='stored', ecu_id=0x7E8)]),
                completed_at=finished)
            self.assertEqual(state.summary, 'Faults found')
            self.assertEqual(state.completed_at, finished)
            self.assertEqual(state.faults[0].title, title)
            self.assertEqual(state.faults[0].reporting_status, 'Confirmed fault')
            self.assertNotIn(code, state.faults[0].explanation)
            self.assertNotIn(code, state.faults[0].recommendation)
            self.assertEqual(state.faults[0].code, code)
            self.assertIn(code, state.details)
            self.assertIn('0x7E8', state.details)

    def test_retained_record_does_not_claim_active_problem(self):
        state = present_diagnostics(self.healthy() | dict(trouble_codes=[
            dict(code='P0300', status='permanent', ecu_id=0x7E8)]))
        self.assertEqual(state.faults[0].reporting_status, 'Retained emissions record')
        self.assertIn('does not by itself prove', state.faults[0].explanation)
        self.assertIn('repair history', state.faults[0].recommendation)
        self.assertFalse(state.mil_on)

    def test_partial_faults_remain_visible_alongside_coverage_warning(self):
        state = present_diagnostics(self.healthy() | dict(completed_services=['monitor', 'stored'],
            trouble_codes=[dict(code='P0171', status='stored', ecu_id=0x7E8)]))
        self.assertEqual(state.status, 'faulted')
        self.assertFalse(state.coverage_complete)
        self.assertIn('Scan incomplete', state.coverage_message)
        self.assertEqual(state.faults[0].title, 'Lean fuel mixture')

    def test_warning_without_retrieved_code_has_explanation(self):
        state = present_diagnostics(self.healthy() | dict(mil_on=True))
        self.assertEqual(state.faults[0].title, 'Check Engine light is on')
        self.assertEqual(state.faults[0].code, '')
        self.assertIn('did not retrieve', state.faults[0].explanation)

    def test_readiness_and_empty_scan_are_distinct_from_fault_free(self):
        not_ready = present_diagnostics(self.healthy() | dict(emissions_ready=False))
        self.assertEqual(not_ready.status, 'not_ready')
        self.assertIn('do not necessarily mean a fault', not_ready.next_action)
        self.assertTrue(not_ready.coverage_complete)
        empty = present_diagnostics({})
        self.assertEqual(empty.summary, 'Scan incomplete')
        self.assertFalse(empty.coverage_complete)
        self.assertIsNone(empty.mil_on)
        self.assertIsNone(empty.emissions_ready)
