"""The developer and full gates share one static check sequence."""

from scripts import quality_gate


def setup_gate(monkeypatch):
    commands = []
    monkeypatch.setattr(quality_gate, "_run_ruff", lambda: True)
    monkeypatch.setattr(quality_gate, "_run_ui_types", lambda: True)
    monkeypatch.setattr(
        quality_gate, "_run", lambda label, command: commands.append(command) or True
    )
    return commands


def test_checks_only_runs_ui_boundaries_once_and_omits_tests(monkeypatch):
    commands = setup_gate(monkeypatch)
    assert quality_gate.main(["--checks-only"]) == 0
    scripts = [command[1] for command in commands]
    assert scripts.count("scripts/check_ui_boundaries.py") == 1
    assert "scripts/check_weather_ui_contracts.py" not in scripts
    assert "scripts/run_tests.py" not in scripts


def test_full_gate_adds_test_suites_once(monkeypatch):
    commands = setup_gate(monkeypatch)
    assert quality_gate.main([]) == 0
    assert [command[1:] for command in commands].count(["scripts/run_tests.py", "all"]) == 1


def test_a_failed_static_check_keeps_gate_failed(monkeypatch):
    setup_gate(monkeypatch)
    monkeypatch.setattr(quality_gate, "_run_ruff", lambda: False)
    assert quality_gate.main(["--checks-only"]) == 1
