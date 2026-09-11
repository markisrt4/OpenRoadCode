# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.automotive.obd2.obd2_poll_scheduler import Obd2PollScheduler
from protocols.obd2.obd_pids import (
    CoolantTempPid,
    EngineLoadPid,
    EngineRpmPid,
    IntakeManifoldPressurePid,
    ThrottlePositionPid,
)


def test_weighted_schedule_matches_expected_request_allocation() -> None:
    rpm = EngineRpmPid()
    map_pid = IntakeManifoldPressurePid()
    throttle = ThrottlePositionPid()
    load = EngineLoadPid()
    coolant = CoolantTempPid()
    scheduler = Obd2PollScheduler(
        rpm=rpm,
        manifold_pressure=map_pid,
        standard=(throttle, load),
        slow=(coolant,),
        supported_pids={rpm.pid, map_pid.pid, throttle.pid, load.pid, coolant.pid},
    )

    pids = [scheduler.next_decoder().pid for _ in range(12)]

    assert pids == [
        rpm.pid,
        map_pid.pid,
        rpm.pid,
        throttle.pid,
        rpm.pid,
        map_pid.pid,
        load.pid,
        rpm.pid,
        coolant.pid,
        map_pid.pid,
        throttle.pid,
        rpm.pid,
    ]


def test_unsupported_pids_are_never_returned() -> None:
    rpm = EngineRpmPid()
    map_pid = IntakeManifoldPressurePid()
    throttle = ThrottlePositionPid()
    scheduler = Obd2PollScheduler(
        rpm=rpm,
        manifold_pressure=map_pid,
        standard=(throttle,),
        slow=(),
        supported_pids={rpm.pid},
    )

    assert [scheduler.next_decoder().pid for _ in range(4)] == [rpm.pid] * 4
