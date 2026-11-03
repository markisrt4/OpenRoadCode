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
