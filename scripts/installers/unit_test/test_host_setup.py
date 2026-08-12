# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the non-mutating host installer planning interface."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INSTALLER = PROJECT_ROOT / "scripts" / "installers" / "host_setup.sh"
FEATURES = PROJECT_ROOT / "scripts" / "installers" / "installer_features.sh"
PERMISSIONS = (
    PROJECT_ROOT
    / "scripts"
    / "installers"
    / "configure_user_permissions.sh"
)


class HostSetupPlanTests(unittest.TestCase):
    def run_installer(
        self,
        *arguments: str,
        distribution: str = "ubuntu",
        distribution_like: str = "debian",
        model: str = "",
        architecture: str = "amd64",
    ) -> subprocess.CompletedProcess[str]:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            os_release = temp_path / "os-release"
            model_file = temp_path / "model"
            os_release.write_text(
                f'ID="{distribution}"\nID_LIKE="{distribution_like}"\n',
                encoding="utf-8",
            )
            model_file.write_text(model, encoding="utf-8")

            environment = os.environ.copy()
            environment.update(
                {
                    "OPENROAD_HOST_ARCH": architecture,
                    "OPENROAD_HOST_SYSTEM": "Linux",
                    "OPENROAD_OS_RELEASE_FILE": str(os_release),
                    "OPENROAD_RPI_MODEL_FILE": str(model_file),
                }
            )
            return subprocess.run(
                [str(INSTALLER), *arguments],
                cwd=PROJECT_ROOT,
                env=environment,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_target_is_required(self) -> None:
        result = self.run_installer("--show-plan")

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--target is required", result.stderr)

    def test_linux_development_plan_excludes_raspberry_pi_support(self) -> None:
        result = self.run_installer("--target", "linux-dev", "--show-plan")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Detected target:       linux-dev", result.stdout)
        self.assertNotIn("raspberry-pi", result.stdout)
        self.assertNotIn("GPIO backend:", result.stdout)
        self.assertIn("VNC service setup:     0", result.stdout)
        self.assertIn("GPSD service setup:    0", result.stdout)

    def test_raspberry_pi_4_plan_selects_legacy_gpio_backend(self) -> None:
        result = self.run_installer(
            "--target",
            "rpi4",
            "--show-plan",
            distribution="raspbian",
            model="Raspberry Pi 4 Model B Rev 1.5",
            architecture="arm64",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("raspberry-pi", result.stdout)
        self.assertIn("GPIO backend:          RPi.GPIO", result.stdout)
        self.assertIn("VNC service setup:     0", result.stdout)
        self.assertIn("GPSD service setup:    0", result.stdout)

    def test_raspberry_pi_5_plan_selects_lgpio_backend(self) -> None:
        result = self.run_installer(
            "--target",
            "rpi5",
            "--show-plan",
            distribution="raspbian",
            model="Raspberry Pi 5 Model B Rev 1.0",
            architecture="arm64",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("GPIO backend:          rpi-lgpio", result.stdout)

    def test_noninteractive_target_mismatch_is_rejected(self) -> None:
        result = self.run_installer(
            "--target",
            "rpi5",
            "--skip-installs",
            "--no-vnc",
            "--no-gpsd-service",
            distribution="raspbian",
            model="Raspberry Pi 4 Model B Rev 1.5",
            architecture="arm64",
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing a noninteractive mismatched install", result.stderr)

    def test_force_target_allows_noninteractive_mismatch(self) -> None:
        result = self.run_installer(
            "--target",
            "rpi5",
            "--force-target",
            "--skip-installs",
            "--no-vnc",
            "--no-gpsd-service",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Requested target:      rpi5", result.stdout)
        self.assertIn("--force-target was supplied", result.stderr)

    def test_additional_features_extend_target_defaults(self) -> None:
        result = self.run_installer(
            "--target",
            "linux-dev",
            "--feature",
            "spotify",
            "--show-plan",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Features:              base spotify", result.stdout)

    def test_default_features_can_be_replaced_by_an_explicit_selection(self) -> None:
        result = self.run_installer(
            "--target",
            "linux-dev",
            "--no-default-features",
            "--feature",
            "base",
            "--feature",
            "spotify",
            "--show-plan",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Features:              base spotify", result.stdout)
        self.assertNotIn("streamlit", result.stdout)

    def test_vnc_service_adds_vnc_and_desktop_capabilities(self) -> None:
        result = self.run_installer(
            "--target",
            "linux-dev",
            "--with-vnc",
            "--show-plan",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Features:              base vnc desktop-ui", result.stdout)
        self.assertIn("VNC service setup:     1", result.stdout)

    def test_concrete_elm327_device_is_not_an_installer_feature(self) -> None:
        result = self.run_installer(
            "--target",
            "linux-dev",
            "--feature",
            "elm327",
            "--show-plan",
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Unknown feature: elm327", result.stderr)

    def test_unknown_feature_is_rejected(self) -> None:
        result = self.run_installer(
            "--target",
            "linux-dev",
            "--feature",
            "bluetooh",
            "--show-plan",
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Unknown feature: bluetooh", result.stderr)

    def test_all_features_on_linux_excludes_raspberry_pi_hardware(self) -> None:
        result = self.run_installer(
            "--target",
            "linux-dev",
            "--all-features",
            "--show-plan",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("desktop-ui", result.stdout)
        self.assertIn("sdrpp", result.stdout)
        self.assertIn("imu", result.stdout)
        self.assertIn("environmental", result.stdout)
        self.assertNotIn("raspberry-pi", result.stdout)
        self.assertNotIn("mpu6050", result.stdout)
        self.assertNotIn("bmp390", result.stdout)

    def test_all_features_on_raspberry_pi_includes_sensor_support(self) -> None:
        result = self.run_installer(
            "--target",
            "rpi5",
            "--all-features",
            "--show-plan",
            distribution="raspbian",
            model="Raspberry Pi 5 Model B Rev 1.0",
            architecture="arm64",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("raspberry-pi", result.stdout)
        self.assertIn("imu", result.stdout)
        self.assertIn("environmental", result.stdout)
        self.assertNotIn("mpu6050", result.stdout)
        self.assertNotIn("bmp388", result.stdout)

    def test_non_debian_distribution_is_rejected(self) -> None:
        result = self.run_installer(
            "--target",
            "linux-dev",
            "--show-plan",
            distribution="fedora",
            distribution_like="",
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Unsupported distribution: fedora", result.stderr)

    def test_portable_base_excludes_raspberry_pi_python_packages(self) -> None:
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; get_feature_python_packages base',
                "feature-test",
                str(FEATURES),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("RPi.GPIO", result.stdout)
        self.assertNotIn("adafruit", result.stdout)

    def test_spotify_audio_packages_follow_install_target(self) -> None:
        linux = subprocess.run(
            [
                "bash", "-c",
                'source "$1"; OPENROAD_INSTALL_TARGET=linux-dev '
                'get_feature_packages spotify',
                "feature-test", str(FEATURES),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        raspberry_pi = subprocess.run(
            [
                "bash", "-c",
                'source "$1"; OPENROAD_INSTALL_TARGET=rpi5 '
                'get_feature_packages spotify',
                "feature-test", str(FEATURES),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("pulseaudio-utils", linux.stdout)
        self.assertIn("wireplumber", raspberry_pi.stdout)
        self.assertIn("pipewire-pulse", raspberry_pi.stdout)
        self.assertIn("alsa-utils", raspberry_pi.stdout)
        self.assertIn("usbutils", raspberry_pi.stdout)

    def test_raspberry_pi_feature_uses_target_selected_gpio_package(self) -> None:
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; get_feature_python_packages raspberry-pi',
                "feature-test",
                str(FEATURES),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("raspberry-pi-gpio-backend", result.stdout)
        self.assertIn("adafruit-blinka", result.stdout)

    def test_permissions_follow_selected_capabilities(self) -> None:
        result = subprocess.run(
            [
                str(PERMISSIONS),
                "--show-plan",
                "input",
                "gps",
                "rtl-sdr",
                "raspberry-pi",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(
            "Feature-requested user groups: input dialout plugdev gpio i2c",
            result.stdout,
        )
        self.assertIn("no user groups were changed", result.stdout)


if __name__ == "__main__":
    unittest.main()
