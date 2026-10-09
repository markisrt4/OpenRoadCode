# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

from datetime import datetime
import math

import pytest

from controllers.automotive import AutomotiveTelemetryProfile, EngineAnalyzer, VehicleConfiguration
from controllers.automotive.obd2.obd2_manager import Obd2Manager
from controllers.automotive.vehicle_state import VehicleState
from messaging.contracts.automotive.vehicle_state_codec import encode_vehicle_state
from messaging.contracts.automotive.vehicle_state_decoder import decode_vehicle_state
from protocols.obd2.obd_pids import ActualEngineTorquePid, ReferenceEngineTorquePid
from protocols.obd2.simulated_obd2_adapter import SimulatedObd2Adapter


def test_standard_torque_decoding_including_engine_braking():
    assert ActualEngineTorquePid().decode(bytes([200])) == 75
    assert ActualEngineTorquePid().decode(bytes([100])) == -25
    assert ActualEngineTorquePid().decode(b'') is None
    assert ReferenceEngineTorquePid().decode(bytes.fromhex('0190')) == 400
    assert ReferenceEngineTorquePid().decode(b'\x01') is None


def test_supported_torque_polls_round_trip_and_derive_power(monkeypatch):
    now = [0.0]
    monkeypatch.setattr('controllers.automotive.obd2.obd2_manager.time.monotonic', lambda: now[0])
    responses = SimulatedObd2Adapter.default_responses()
    responses[0x40] = (int.from_bytes(responses[0x40], 'big') | 1).to_bytes(4, 'big')
    responses[0x60] = bytes.fromhex('60000000')
    responses[0x62] = bytes([200])
    responses[0x63] = bytes.fromhex('0190')
    adapter = SimulatedObd2Adapter(responses)
    manager = Obd2Manager(adapter)
    manager.connect()
    manager.set_telemetry_profile(AutomotiveTelemetryProfile.ECU)
    adapter.requests.clear()
    for _ in range(80):
        before = len(adapter.requests)
        state = manager.read_state()
        assert len(adapter.requests)-before <= 1
    decoded = decode_vehicle_state(encode_vehicle_state(state)).data
    analysis = EngineAnalyzer(VehicleConfiguration()).analyze(decoded)
    assert analysis.reported_torque_nm == 300
    assert analysis.reported_power_w == pytest.approx(300*3000*math.tau/60)
    now[0] = 11
    monkeypatch.setattr(adapter, 'request', lambda request: ())
    assert manager.read_state().actual_engine_torque_ratio is None


def test_unsupported_torque_is_not_requested_or_guessed():
    adapter = SimulatedObd2Adapter()
    manager = Obd2Manager(adapter)
    manager.connect()
    manager.set_telemetry_profile(AutomotiveTelemetryProfile.ECU)
    adapter.requests.clear()
    for _ in range(80):
        state = manager.read_state()
    assert all(request.pid not in (0x62, 0x63) for request in adapter.requests)
    assert state.actual_engine_torque_ratio is None
    assert EngineAnalyzer(VehicleConfiguration()).analyze(state).reported_power_w is None


@pytest.mark.parametrize(('ratio', 'reference', 'rpm', 'torque', 'power'), [
    (0.5, 400, 100, 200, 20000), (-0.25, 400, 100, -100, -10000),
    (0.0, 400, 100, 0, 0), (0.5, 0, 100, None, None),
    (None, 400, 100, None, None), (0.5, 400, None, 200, None),
])
def test_output_requires_reported_values(ratio, reference, rpm, torque, power):
    state = VehicleState(timestamp=datetime.now(), actual_engine_torque_ratio=ratio,
                         reference_engine_torque_nm=reference, engine_speed_rad_s=rpm)
    result = EngineAnalyzer(VehicleConfiguration()).analyze(state)
    assert result.reported_torque_nm == torque
    assert result.reported_power_w == power


def test_v4_messages_still_decode_without_torque():
    payload = encode_vehicle_state(VehicleState(timestamp=datetime.now()))
    payload['version'] = 4
    payload['data'].pop('actual_engine_torque_ratio')
    payload['data'].pop('reference_engine_torque_nm')
    assert decode_vehicle_state(payload).data.actual_engine_torque_ratio is None
