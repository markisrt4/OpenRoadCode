
from __future__ import annotations

from protocols.obd2 import (
    AcceleratorPedalPositionPid,
    BarometricPressurePid,
    ControlModuleVoltagePid,
    CoolantTempPid,
    EngineLoadPid,
    EngineRpmPid,
    FuelLevelPid,
    IntakeAirTempPid,
    IntakeManifoldPressurePid,
    MassAirFlowPid,
    Obd2Request,
    Obd2Response,
    ThrottlePositionPid,
    VehicleSpeedPid,
)


def _close(actual: float | None, expected: float, tolerance: float = 1e-6) -> None:
    assert actual is not None
    assert abs(actual - expected) <= tolerance, (actual, expected)


def main() -> None:
    request = Obd2Request(mode=0x01, pid=0x0C)
    assert request.mode == 0x01
    assert request.pid == 0x0C

    response = Obd2Response(mode=0x41, pid=0x0C, data=bytes.fromhex("1AF8"), ecu_id=0x7E8)
    assert response.mode == 0x41
    assert response.ecu_id == 0x7E8

    _close(EngineLoadPid().decode(bytes([128])), 128 * 100.0 / 255.0)
    _close(EngineRpmPid().decode(bytes.fromhex("1AF8")), 1726.0)
    assert VehicleSpeedPid().decode(bytes([100])) == 100
    assert IntakeManifoldPressurePid().decode(bytes([98])) == 98
    assert BarometricPressurePid().decode(bytes([101])) == 101
    _close(ThrottlePositionPid().decode(bytes([255])), 100.0)
    _close(AcceleratorPedalPositionPid().decode(bytes([128])), 128 * 100.0 / 255.0)
    assert CoolantTempPid().decode(bytes([120])) == 80
    assert IntakeAirTempPid().decode(bytes([70])) == 30
    _close(MassAirFlowPid().decode(bytes.fromhex("1388")), 50.0)
    _close(FuelLevelPid().decode(bytes([128])), 128 * 100.0 / 255.0)
    _close(ControlModuleVoltagePid().decode(bytes.fromhex("3039")), 12.345)

    decoders = (
        EngineLoadPid(), EngineRpmPid(), VehicleSpeedPid(),
        IntakeManifoldPressurePid(), BarometricPressurePid(),
        ThrottlePositionPid(), AcceleratorPedalPositionPid(),
        CoolantTempPid(), IntakeAirTempPid(), MassAirFlowPid(),
        FuelLevelPid(), ControlModuleVoltagePid(),
    )
    for decoder in decoders:
        assert decoder.mode == 0x01
        assert decoder.decode(b"") is None
        assert decoder.unit

    print("OBD-II protocol component test: PASS")


if __name__ == "__main__":
    main()
