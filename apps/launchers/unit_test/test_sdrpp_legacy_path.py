# SPDX-License-Identifier: MIT

import subprocess
from unittest.mock import patch

import pytest

from apps.launchers.sdrpp_launcher import _termux_source_selection


@pytest.mark.parametrize("managed_exists,legacy_exists,explicit", [
    (True, True, False), (False, True, False), (False, False, False),
    (False, True, True),
])
def test_guest_selection_prefers_managed_and_preserves_explicit_path(tmp_path, managed_exists, legacy_exists, explicit):
    managed, legacy, custom = (tmp_path / name for name in ("managed build", "legacy build", "custom build"))
    for path, exists in ((managed, managed_exists), (legacy, legacy_exists)):
        if exists:
            (path / "build").mkdir(parents=True)
            binary = path / "build/sdrpp"
            binary.write_text("#!/bin/sh\n")
            binary.chmod(0o755)
    requested = custom if explicit else managed
    with patch("apps.launchers.sdrpp_launcher.DEFAULT_TERMUX_SDRPP_SOURCE", managed), patch(
        "apps.launchers.sdrpp_launcher.DEFAULT_TERMUX_LEGACY_SDRPP_SOURCE", legacy):
        selection = _termux_source_selection(requested)
    result = subprocess.run(["bash", "-c", selection + '; printf "%s" "$sdrpp_source"'],
                            check=True, capture_output=True, text=True)
    expected = custom if explicit else legacy if not managed_exists and legacy_exists else managed
    assert result.stdout == str(expected)
