# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.automotive.obd2.obd2_poll_scheduler import (
    Obd2PollingProfile,
    Obd2PollScheduler,
)
from protocols.obd2.obd_pids import (
    CoolantTempPid,
    EngineLoadPid,
    EngineRpmPid,
    IgnitionTimingAdvancePid,
    IntakeManifoldPressurePid,
    ShortTermFuelTrimBank1Pid,
    ThrottlePositionPid,
)


def _scheduler() -> Obd2PollScheduler:
    rpm = EngineRpmPid()
    map_pid = IntakeManifoldPressurePid()
    throttle = ThrottlePositionPid()
    load = EngineLoadPid()
    coolant = CoolantTempPid()
    timing = IgnitionTimingAdvancePid()
    trim = ShortTermFuelTrimBank1Pid()
    supported = {p.pid for p in (rpm, map_pid, throttle, load, coolant, timing, trim)}
    return Obd2PollScheduler(
        rpm=rpm,
        manifold_pressure=map_pid,
        standard=(throttle, load),
        slow=(coolant,),
        performance=(throttle, timing),
        engine=(load, coolant, timing),
        ecu=(trim, timing),
        trip=(load,),
        supported_pids=supported,
    )


def test_background_profile_is_trip_biased() -> None:
    scheduler = _scheduler()
    pids = [scheduler.next_decoder().pid for _ in range(12)]
    assert pids == [
        0x04, 0x11, 0x04, 0x0C, 0x04, 0x05,
        0x04, 0x0B, 0x04, 0x04, 0x11, 0x04,
    ]



def test_home_profile_keeps_glance_metrics_fresh() -> None:
    scheduler = _scheduler()
    scheduler.set_profile(Obd2PollingProfile.HOME)
    pids = [scheduler.next_decoder().pid for _ in range(12)]

    assert pids.count(0x0C) == 3
    assert pids.count(0x0B) == 2
    assert 0x04 in pids
    assert 0x05 in pids


def test_ecu_profile_prioritizes_ecu_group() -> None:
    scheduler = _scheduler()
    scheduler.set_profile(Obd2PollingProfile.ECU)
    pids = [scheduler.next_decoder().pid for _ in range(12)]

    assert pids.count(0x06) >= 2
    assert pids.count(0x0E) >= 2
    assert 0x0C in pids
    assert 0x0B in pids


def test_profile_change_resets_schedule_position() -> None:
    scheduler = _scheduler()
    scheduler.next_decoder()
    scheduler.next_decoder()

    scheduler.set_profile(Obd2PollingProfile.ECU)

    assert scheduler.profile is Obd2PollingProfile.ECU
    assert scheduler.next_decoder().pid == 0x06


def test_unsupported_pids_are_never_returned() -> None:
    rpm = EngineRpmPid()
    scheduler = Obd2PollScheduler(
        rpm=rpm,
        manifold_pressure=IntakeManifoldPressurePid(),
        standard=(ThrottlePositionPid(),),
        slow=(),
        supported_pids={rpm.pid},
    )

    assert [scheduler.next_decoder().pid for _ in range(4)] == [rpm.pid] * 4
