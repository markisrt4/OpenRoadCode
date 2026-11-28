"""Hardware-independent runtime feature selection tests."""

import argparse

from apps.orcUi.runtime_features import RuntimeFeatures, add_runtime_arguments


def resolve(arguments, environment=None):
    parser = argparse.ArgumentParser()
    add_runtime_arguments(parser)
    return RuntimeFeatures.resolve(parser.parse_args(arguments), environment or {})


def test_normal_defaults():
    assert resolve([]) == RuntimeFeatures(True, True, True, True, True, True)


def test_simulation_defaults():
    assert resolve(["--simulation"]) == RuntimeFeatures(False, False, False, False, False, False)


def test_explicit_overrides():
    assert resolve(["--simulation", "--camera", "--opengl"]) == RuntimeFeatures(
        True, False, False, False, True, False
    )


def test_environment_defaults_and_explicit_override():
    environment = {"ORC_NO_AUDIO": "1", "ORC_NO_CAMERA": "1"}
    assert resolve(["--camera"], environment) == RuntimeFeatures(
        True, False, True, True, True, True
    )


def test_environment_simulation():
    assert resolve([], {"ORC_SIMULATION": "1"}) == RuntimeFeatures(
        False, False, False, False, False, False
    )


def test_publish_compatibility_flags():
    environment = {}
    resolve(["--no-opengl", "--no-native-map"]).apply(environment)
    assert environment == {
        "ORC_NO_CAMERA": "0",
        "ORC_NO_AUDIO": "0",
        "ORC_NO_NATIVE_MAP": "1",
        "ORC_NO_SPOTIFY": "0",
        "ORC_NO_OPENGL": "1",
        "ORC_NO_ADSB": "0",
    }
