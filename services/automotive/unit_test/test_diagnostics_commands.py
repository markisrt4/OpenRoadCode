# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Exercise the real runtime, scheduler and ZeroMQ path without physical hardware."""
import threading
import time
import unittest
import zmq
from controllers.automotive.obd2.obd2_manager import Obd2Manager
from controllers.automotive.obd2.obd2_poll_scheduler import Obd2PollingProfile
from controllers.automotive.obd2.elm327_obd_adapter import Elm327ObdAdapter
from controllers.automotive.composite_vehicle_state_source import CompositeVehicleStateSource
from controllers.automotive.obd2.unit_test.test_obd2_diagnostics import _Adapter
from hardware_io.automotive.elm327.elm327_response import Elm327Response
from protocols.obd2 import Obd2CommandError, Obd2ConnectionError, Obd2Response, Obd2Request
from services.automotive.automotive_runtime import AutomotiveRuntime
from services.automotive.automotive_command_client import AutomotiveCommandClient
from services.automotive.automotive_command_service import SCAN_DIAGNOSTICS_COMMAND
from services.automotive.zeromq_automotive_command_server import ZeroMqAutomotiveCommandServer

class _Publisher:
    def __init__(self):
        self.count = 0
        self.states = []
    def publish(self, *args, **kwargs):
        self.count += 1
        self.states.append(args[1]["data"])

class _TrackedAdapter(_Adapter):
    def __init__(self):
        super().__init__({
            (1, 0x0C): (Obd2Response(0x41, 0x0C, bytes.fromhex('1F40'), 0x7E8),),
            (1, 0x0D): (Obd2Response(0x41, 0x0D, bytes.fromhex('3C'), 0x7E8),),
            (1, 0x0B): (Obd2Response(0x41, 0x0B, bytes.fromhex('50'), 0x7E8),),
            (1, 1): (Obd2Response(0x41, 1, bytes.fromhex('81072100'), 0x7E8),),
            (3, None): (Obd2Response(0x43, None, bytes.fromhex('0300'), 0x7E8),),
            (7, None): (Obd2Response(0x47, None, bytes.fromhex('0000'), 0x7E8),),
            (10, None): (Obd2Response(0x4A, None, bytes.fromhex('0000'), 0x7E8),),
        })
        self.owners = set()
        self.connected = threading.Event()
        self.finished = threading.Event()
    def connect(self):
        self.owners.add(threading.get_ident())
        self.connected.set()
    def disconnect(self):
        self.owners.add(threading.get_ident())
        self.finished.set()
    def request(self, request):
        self.owners.add(threading.get_ident())
        return super().request(request)

def _wait(predicate):
    deadline = time.monotonic() + 2
    while not predicate() and time.monotonic() < deadline:
        time.sleep(.001)
    assert predicate(), 'operation did not complete'

class DiagnosticsCommandsTest(unittest.TestCase):
    def test_scan_over_bound_zmq_listener_keeps_owner_and_telemetry_alive(self):
        adapter = _TrackedAdapter()
        publisher = _Publisher()
        manager = Obd2Manager(adapter)
        manager.set_polling_profile(Obd2PollingProfile.PERFORMANCE)
        runtime = AutomotiveRuntime(manager, publisher, rate_hz=100)
        thread = threading.Thread(target=runtime.run)
        thread.start()
        server = ZeroMqAutomotiveCommandServer(runtime, 'tcp://127.0.0.1:*')
        server_thread = threading.Thread(target=server.run)
        server_thread.start()
        try:
            _wait(lambda: server.is_running and runtime._connected)
            client = AutomotiveCommandClient(server.bound_endpoint)
            _wait(lambda: publisher.states and all(
                publisher.states[-1][key] is not None for key in
                ('engine_speed_rad_s', 'vehicle_speed_m_s', 'intake_manifold_pressure_pa')
            ))
            before = publisher.count
            result = client.scan_diagnostics()
            self.assertTrue(result['mil_on'])
            self.assertEqual(result['trouble_codes'][0]['code'], 'P0300')
            self.assertEqual(set(result['completed_services']), {'monitor', 'stored', 'pending', 'permanent'})
            self.assertGreaterEqual(publisher.count - before, 7)
            self.assertTrue(any(mode == 1 and pid != 1 for mode, pid in adapter.requests))
            _wait(lambda: runtime._command_future is None)
            self.assertEqual(client.scan_diagnostics()['trouble_codes'][0]['code'], 'P0300')
            for key in ('engine_speed_rad_s', 'vehicle_speed_m_s', 'intake_manifold_pressure_pa'):
                self.assertTrue(any(state[key] is not None for state in publisher.states), key)
        finally:
            server.close()
            runtime.close()
            thread.join(2)
            server_thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertFalse(server_thread.is_alive())
        self.assertEqual(len(adapter.owners), 1)
        self.assertTrue(adapter.finished.is_set())

    def test_concurrent_scan_rejected_and_shutdown_releases_pending_scan(self):
        adapter = _TrackedAdapter()
        manager = Obd2Manager(adapter)
        runtime = AutomotiveRuntime(manager, _Publisher())
        runtime._running = runtime._connected = True
        future = runtime.request_command(SCAN_DIAGNOSTICS_COMMAND)
        _wait(lambda: manager._diagnostics_session is not None)
        self.assertFalse(runtime.request_command(SCAN_DIAGNOSTICS_COMMAND).result()['ok'])
        runtime._running = False
        runtime.close()
        self.assertFalse(future.result(timeout=1)['ok'])

    def test_timeout_clears_session_and_optional_service_rejection_is_not_disconnect(self):
        manager = Obd2Manager(_TrackedAdapter())
        with self.assertRaises(TimeoutError):
            manager.scan_diagnostics(timeout_s=.01)
        self.assertIsNone(manager._diagnostics_session)
        class Rejected(_TrackedAdapter):
            def request(self, request):
                if request.mode == 7:
                    raise Obd2CommandError('unsupported')
                return super().request(request)
        manager = Obd2Manager(Rejected())
        result = []
        worker = threading.Thread(target=lambda: result.append(manager.scan_diagnostics(timeout_s=1)))
        worker.start()
        _wait(lambda: manager._diagnostics_session is not None)
        for _ in range(7):
            manager.read_state()
        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertNotIn('pending', result[0].completed_services)

    def test_server_shutdown_releases_transport_wait(self):
        from concurrent.futures import Future
        from unittest.mock import Mock
        runtime = Mock()
        runtime.request_command.return_value = Future()
        server = ZeroMqAutomotiveCommandServer(runtime)
        replies = []
        waiter = threading.Thread(target=lambda: replies.append(server._handle_request(
            {"command": SCAN_DIAGNOSTICS_COMMAND})))
        waiter.start()
        _wait(lambda: runtime.request_command.called)
        server.close()
        waiter.join(1)
        self.assertFalse(waiter.is_alive())
        self.assertFalse(replies[0]['ok'])

    def test_composite_scan_uses_engine_only(self):
        from unittest.mock import Mock
        engine, motion = Mock(), Mock()
        source = CompositeVehicleStateSource(engine, motion)
        self.assertIs(source.scan_diagnostics(timeout_s=2), engine.scan_diagnostics.return_value)
        engine.scan_diagnostics.assert_called_once_with(timeout_s=2)
        motion.scan_diagnostics.assert_not_called()

    def test_transport_loss_wakes_waiter_and_propagates_to_runtime(self):
        class Lost(_TrackedAdapter):
            def request(self, request):
                raise Obd2ConnectionError('lost')
        manager = Obd2Manager(Lost())
        errors = []
        def scan():
            try:
                manager.scan_diagnostics(timeout_s=1)
            except RuntimeError as error:
                errors.append(str(error))
        worker = threading.Thread(target=scan)
        worker.start()
        _wait(lambda: manager._diagnostics_session is not None)
        with self.assertRaises(Obd2ConnectionError):
            manager.read_state()
        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertIn('lost', errors[0])

    def test_android_wire_examples_decode_with_production_adapter(self):
        for request, wire in [
            (Obd2Request(1, 1), '7E806410100072121'),
            (Obd2Request(3), '7E803430300'),
            (Obd2Request(7), '7E803470000'),
            (Obd2Request(10), '7E8034A0000'),
        ]:
            response = Elm327Response(command='', raw=wire, lines=(wire,))
            decoded = Elm327ObdAdapter._parse_response(request, response)
            self.assertEqual(decoded[0].ecu_id, 0x7E8)
        response = Elm327Response(command='0101', raw='', lines=('7E806410100072121',))
        monitor = Elm327ObdAdapter._parse_response(Obd2Request(1, 1), response)
        from controllers.automotive.obd2.obd2_diagnostics import Obd2DiagnosticsScanner
        self.assertFalse(Obd2DiagnosticsScanner.decode(monitor, (), (), ()).emissions_ready)
