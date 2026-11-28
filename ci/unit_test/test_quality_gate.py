"""The developer and full gates share one static check sequence."""

from ci import quality_gate


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
    assert scripts.count("ci/check_ui_boundaries.py") == 1
    assert "ci/check_weather_ui_contracts.py" not in scripts
    assert "ci/run_tests.py" not in scripts


def test_full_gate_adds_test_suites_once(monkeypatch):
    commands = setup_gate(monkeypatch)
    assert quality_gate.main([]) == 0
    assert [command[1:] for command in commands].count(["ci/run_tests.py", "all"]) == 1


def test_a_failed_static_check_keeps_gate_failed(monkeypatch):
    setup_gate(monkeypatch)
    monkeypatch.setattr(quality_gate, "_run_ruff", lambda: False)
    assert quality_gate.main(["--checks-only"]) == 1


def test_static_gate_includes_portable_documentation_checks(monkeypatch):
    commands = setup_gate(monkeypatch)
    assert quality_gate.main(["--checks-only"]) == 0
    arguments = [command[1:] for command in commands]
    assert arguments.count(["ci/docs_inventory.py", "--check"]) == 1
    assert arguments.count(["ci/check_markdown_links.py"]) == 1
    assert arguments.count(["ci/check_doxygen_contracts.py"]) == 1
