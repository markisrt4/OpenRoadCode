"""Tests for deployment-target detection."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.runtime_target import RuntimeTarget, detect_runtime_target


class RuntimeTargetTest(unittest.TestCase):
    def test_non_pi_host_defaults_to_linux_dev(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIs(
                detect_runtime_target(model_path="/missing/model"),
                RuntimeTarget.LINUX_DEV,
            )

    def test_pi_model_selects_pi_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model"
            model.write_text("Raspberry Pi 5 Model B Rev 1.0\0")
            with patch.dict(os.environ, {}, clear=True):
                self.assertIs(
                    detect_runtime_target(model_path=model),
                    RuntimeTarget.RPI5,
                )

    def test_environment_override_takes_precedence(self) -> None:
        with patch.dict(
            os.environ, {"OPENROAD_RUNTIME_TARGET": "rpi4"}, clear=True
        ):
            self.assertIs(detect_runtime_target(), RuntimeTarget.RPI4)


if __name__ == "__main__":
    unittest.main()
