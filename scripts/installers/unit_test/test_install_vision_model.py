# SPDX-License-Identifier: MIT
"""Exercise verified model installation with an offline download double."""

import hashlib
import io
from unittest.mock import Mock

from scripts.installers import install_vision_model as installer


def test_installs_verified_model_and_skips_download_on_rerun(monkeypatch, tmp_path):
    model = b"fixture weights"
    target = tmp_path / "vision/models/yolo11n.pt"
    download = Mock(return_value=io.BytesIO(model))
    monkeypatch.setattr(installer, "vision_model_path", lambda: target)
    monkeypatch.setattr(installer, "MODEL_SIZE", len(model))
    monkeypatch.setattr(installer, "MODEL_SHA256", hashlib.sha256(model).hexdigest())
    monkeypatch.setattr(installer, "urlopen", download)

    assert installer.main() == 0
    assert installer.main() == 0
    assert target.read_bytes() == model
    download.assert_called_once()


def test_invalid_download_preserves_existing_file(monkeypatch, tmp_path):
    target = tmp_path / "yolo11n.pt"
    target.write_bytes(b"previous model")
    monkeypatch.setattr(installer, "vision_model_path", lambda: target)
    monkeypatch.setattr(installer, "urlopen", lambda *args, **kwargs: io.BytesIO(b"bad data"))

    assert installer.main() == 1
    assert target.read_bytes() == b"previous model"
