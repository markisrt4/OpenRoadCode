"""Explicit developer targets avoid suite-wide discovery and preserve pytest flags."""

import subprocess
from unittest.mock import Mock

from scripts import run_tests


def test_selected_targets_do_not_expand_to_all_suites(monkeypatch):
    discover = Mock(side_effect=AssertionError("Broad discovery was not requested"))
    execute = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(run_tests, "find_requested_suites", discover)
    monkeypatch.setattr(run_tests.subprocess, "run", execute)
    target = "frontends/tk/media/unit_test/test_media_screen.py::MediaScreenTest"
    assert run_tests.main(["unit", target, "-k", "secondary_actions"]) == 0
    assert execute.call_args.args[0][4:] == [target, "-k", "secondary_actions"]
    discover.assert_not_called()


def test_empty_focused_selection_does_not_report_success(monkeypatch):
    monkeypatch.setattr(
        run_tests.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], run_tests.PYTEST_NO_TESTS_COLLECTED)),
    )
    assert run_tests.main(["unit", "path/to/tests", "-k", "no_matches"]) == 1


def test_full_categories_still_discover_all_requested_suites(monkeypatch, tmp_path):
    suite = tmp_path / "example/unit_test"
    discover = Mock(return_value=(suite,))
    execute = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(run_tests, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(run_tests, "find_requested_suites", discover)
    monkeypatch.setattr(run_tests.subprocess, "run", execute)
    assert run_tests.main(["all"]) == 0
    discover.assert_called_once_with(("unit", "integration"))
    assert execute.call_args.args[0][4:] == ["example/unit_test"]
