# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

from apps.orcUi.frontend.tk.ecu_update_rate import RateCounter, format_fps


def test_rates_measure_elapsed_time_and_go_zero_when_stopped():
    now = [0.0]
    counter = RateCounter(clock=lambda: now[0])
    for _ in range(4):
        counter.record_update()
    for _ in range(40):
        counter.record_frame()
    now[0] = 2.0
    rates = counter.sample()
    assert rates.telemetry_hz == 2
    assert rates.render_hz == 20
    counter.record_update()
    now[0] = 3.0
    rates = counter.sample()
    assert rates.telemetry_hz == 1
    assert rates.render_hz == 0
    now[0] = 4.0
    assert counter.sample().telemetry_hz == 0


def test_fps_label_omits_the_telemetry_rate():
    assert format_fps(19.95) == "19.9 FPS"
