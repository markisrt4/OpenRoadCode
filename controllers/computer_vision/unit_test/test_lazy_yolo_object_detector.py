# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from controllers.computer_vision.yolo_object_detector import LazyYoloObjectDetector


def test_lazy_detector_prepares_model_only_on_first_inference() -> None:
    readiness = Mock(model_name="yolo11n.pt")
    model = readiness.prepare.return_value
    detector = Mock()
    factory = Mock(return_value=detector)
    lazy = LazyYoloObjectDetector(
        readiness,
        confidence=0.10,
        image_size=640,
        detector_factory=factory,
    )
    first, second = Mock(), Mock()

    assert lazy.detect(first) is detector.detect.return_value
    assert lazy.detect(second) is detector.detect.return_value

    readiness.prepare.assert_called_once_with()
    factory.assert_called_once_with(
        "yolo11n.pt",
        confidence=0.10,
        image_size=640,
        model=model,
    )
    assert detector.detect.call_args_list[0].args == (first,)
    assert detector.detect.call_args_list[1].args == (second,)
