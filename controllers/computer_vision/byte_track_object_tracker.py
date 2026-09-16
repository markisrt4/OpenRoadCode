# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ByteTrack adapter for OpenRoadCode normalized detections."""

from __future__ import annotations

from controllers.computer_vision.object_detector_if import DetectionFrame
from controllers.computer_vision.object_tracker_if import ObjectTrack, ObjectTrackerIf, TrackFrame


class ByteTrackObjectTracker(ObjectTrackerIf):
    """Track detections with Supervision's ByteTrack implementation."""

    def __init__(self, *, frame_rate: int = 30) -> None:
        try:
            import supervision as sv
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "supervision is required for ByteTrack; run the camera perception setup script"
            ) from exc
        self._sv = sv
        self._frame_rate = frame_rate
        self._tracker = sv.ByteTrack(frame_rate=frame_rate)
        self._first_seen: dict[int, float] = {}
        self._labels: dict[int, str] = {}

    def reset(self) -> None:
        self._tracker = self._sv.ByteTrack(frame_rate=self._frame_rate)
        self._first_seen.clear()
        self._labels.clear()

    def update(self, detections: DetectionFrame) -> TrackFrame:
        import numpy as np

        source = detections.detections
        if source:
            xyxy = np.asarray(
                [[d.x, d.y, d.x + d.width, d.y + d.height] for d in source],
                dtype=np.float32,
            )
            confidence = np.asarray([d.confidence for d in source], dtype=np.float32)
            # ByteTrack requires a numeric class id. Stable per-frame label ids
            # are sufficient because ORC preserves the authoritative text label
            # separately and resolves it by overlap below.
            labels = sorted({d.label for d in source})
            label_to_id = {label: index for index, label in enumerate(labels)}
            class_id = np.asarray([label_to_id[d.label] for d in source], dtype=int)
            sv_detections = self._sv.Detections(
                xyxy=xyxy,
                confidence=confidence,
                class_id=class_id,
            )
        else:
            sv_detections = self._sv.Detections.empty()

        tracked = self._tracker.update_with_detections(sv_detections)
        result: list[ObjectTrack] = []
        tracker_ids = tracked.tracker_id
        if tracker_ids is None:
            return TrackFrame(detections.timestamp_s, detections.sequence, ())

        for index, raw_id in enumerate(tracker_ids):
            track_id = int(raw_id)
            x1, y1, x2, y2 = (float(v) for v in tracked.xyxy[index])
            confidence = (
                float(tracked.confidence[index])
                if tracked.confidence is not None
                else 0.0
            )
            label = self._match_label(x1, y1, x2, y2, source)
            if label is not None:
                self._labels[track_id] = label
            else:
                label = self._labels.get(track_id, "object")

            first_seen = self._first_seen.setdefault(track_id, detections.timestamp_s)
            result.append(
                ObjectTrack(
                    track_id=track_id,
                    label=label,
                    confidence=max(0.0, min(1.0, confidence)),
                    x=max(0.0, min(1.0, x1)),
                    y=max(0.0, min(1.0, y1)),
                    width=max(0.0, min(1.0, x2) - max(0.0, min(1.0, x1))),
                    height=max(0.0, min(1.0, y2) - max(0.0, min(1.0, y1))),
                    age_s=max(0.0, detections.timestamp_s - first_seen),
                )
            )

        return TrackFrame(detections.timestamp_s, detections.sequence, tuple(result))

    @staticmethod
    def _match_label(x1: float, y1: float, x2: float, y2: float, source) -> str | None:
        """Return the source label with greatest IoU for one tracked box."""
        best_label = None
        best_iou = 0.0
        for detection in source:
            dx1, dy1 = detection.x, detection.y
            dx2, dy2 = dx1 + detection.width, dy1 + detection.height
            ix1, iy1 = max(x1, dx1), max(y1, dy1)
            ix2, iy2 = min(x2, dx2), min(y2, dy2)
            intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
            union = (x2 - x1) * (y2 - y1) + detection.width * detection.height - intersection
            iou = intersection / union if union > 0.0 else 0.0
            if iou > best_iou:
                best_iou = iou
                best_label = detection.label
        return best_label
