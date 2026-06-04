"""
Store Intelligence System — Phase 2
tracking.py

Multi-object tracking of persons from CCTV video using YOLOv8 & built-in ByteTrack.
Clean architecture: configuration, domain models, annotator, runner, and CLI 
are kept in clearly separated layers within this single module.

Usage:
    python tracking.py --source "CAM 1.mp4" --output "tracked_output.mp4" --tracks-file "tracks.json"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("store_intelligence.tracking")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TrackingConfig:
    """Immutable runtime configuration for the person tracker."""

    model_path: str = "yolov8n.pt"          # YOLOv8 weights file
    confidence_threshold: float = 0.50       # minimum detection confidence
    iou_threshold: float = 0.45             # NMS IoU threshold
    device: str = "cpu"                     # 'cpu', '0', 'mps'
    show_preview: bool = False               # display annotated frames live
    save_output: bool = True                # write annotated video to disk
    output_path: str = "tracked_output.mp4" # path for saved output video
    tracks_file: str = "tracks.json"        # path for exported JSON track records
    max_frames: int = 0                     # 0 = process entire source
    trail_len: int = 45                     # maximum points to keep for motion trails


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------
@dataclass
class TrackState:
    """
    In-memory record of a specific track's lifecycle and visibility.
    Used for motion trail rendering and session analytics.
    """

    track_id: int
    first_seen_frame: int
    last_seen_frame: int
    total_frames_visible: int = 0
    trail: deque[Tuple[int, int]] = field(default_factory=lambda: deque(maxlen=45))

    def update(self, frame_id: int, center: Tuple[int, int]) -> None:
        """Update track visibility information and trail history."""
        self.last_seen_frame = frame_id
        self.total_frames_visible += 1
        self.trail.append(center)


class TrackRegistry:
    """Manages active track histories and session analytics statistics."""

    def __init__(self, config: TrackingConfig) -> None:
        self.config = config
        self.registry: Dict[int, TrackState] = {}

    def update_track(self, track_id: int, frame_id: int, center: Tuple[int, int]) -> TrackState:
        """Register or update an active track ID in-memory."""
        if track_id not in self.registry:
            self.registry[track_id] = TrackState(
                track_id=track_id,
                first_seen_frame=frame_id,
                last_seen_frame=frame_id,
                trail=deque(maxlen=self.config.trail_len)
            )
        state = self.registry[track_id]
        state.update(frame_id, center)
        return state

    def get_trail(self, track_id: int) -> List[Tuple[int, int]]:
        """Get the coordinates history list for a track."""
        if track_id in self.registry:
            return list(self.registry[track_id].trail)
        return []

    def get_statistics(self) -> dict:
        """Compute end-of-run tracking metrics."""
        total_tracks = len(self.registry)
        if total_tracks == 0:
            return {
                "total_tracks": 0,
                "avg_track_length": 0,
                "max_track_length": 0
            }
        
        track_lengths = [t.total_frames_visible for t in self.registry.values()]
        return {
            "total_tracks": total_tracks,
            "avg_track_length": round(sum(track_lengths) / total_tracks, 1),
            "max_track_length": max(track_lengths)
        }


# ---------------------------------------------------------------------------
# Visual Annotation layer
# ---------------------------------------------------------------------------
class TrackAnnotator:
    """Draws tracked persons, ID labels, and motion trails with smooth color schemes."""

    # 30 high-contrast BGR colors
    _COLOR_PALETTE: List[Tuple[int, int, int]] = [
        (255, 100, 60), (60, 200, 255), (100, 255, 100), (255, 60, 180),
        (255, 200, 60), (140, 60, 255), (60, 255, 200), (255, 140, 60),
        (60, 60, 255), (200, 255, 60), (255, 60, 60), (60, 255, 140),
        (255, 180, 100), (100, 60, 255), (60, 180, 255), (255, 255, 100),
        (180, 255, 60), (255, 60, 140), (60, 255, 60), (100, 180, 255),
        (255, 100, 180), (180, 60, 255), (60, 255, 255), (255, 220, 60),
        (255, 60, 255), (100, 255, 180), (255, 140, 100), (60, 100, 255),
        (200, 60, 255), (60, 140, 255),
    ]

    @classmethod
    def _get_color(cls, track_id: int) -> Tuple[int, int, int]:
        return cls._COLOR_PALETTE[track_id % len(cls._COLOR_PALETTE)]

    @classmethod
    def draw(
        cls,
        frame: cv2.Mat,
        tracks: List[dict],
        registry: TrackRegistry
    ) -> cv2.Mat:
        """
        Draw bounding boxes, labels, center dots, and motion trails.
        
        Annotation style:
          - Distinct colored bounding boxes per track ID.
          - Filled label bar on top: 'Person #<track_id>' (e.g. 'Person #1').
          - Fading trail line tracing recent path history.
          - Center dot ('•') highlighting the current location.
        """
        annotated = frame.copy()
        FONT = cv2.FONT_HERSHEY_SIMPLEX
        FONT_SCALE = 0.50
        THICKNESS = 2

        for t in tracks:
            track_id = t["track_id"]
            x1, y1, x2, y2 = t["bbox"]
            color = cls._get_color(track_id)

            # 1. Bounding Box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, THICKNESS)

            # 2. Label text and background
            label = f"Person #{track_id}"
            (lw, lh), baseline = cv2.getTextSize(label, FONT, FONT_SCALE, 1)
            ly1 = max(y1 - lh - baseline - 6, 0)
            ly2 = y1
            cv2.rectangle(annotated, (x1, ly1), (x1 + lw + 8, ly2), color, -1)
            cv2.putText(
                annotated, label,
                (x1 + 4, ly2 - baseline - 2),
                FONT, FONT_SCALE, (255, 255, 255), 1, cv2.LINE_AA
            )

            # 3. Motion Trail Visualization
            trail = registry.get_trail(track_id)
            if len(trail) > 1:
                for i in range(1, len(trail)):
                    # Fade segments based on relative age
                    fraction = i / len(trail)
                    thickness = max(1, int(3 * fraction))
                    faded_color = tuple(max(0, min(255, int(c * fraction))) for c in color)
                    cv2.line(annotated, trail[i - 1], trail[i], faded_color, thickness, cv2.LINE_AA)

            # 4. Center Dot
            cx, cy = t["center"]
            cv2.circle(annotated, (cx, cy), 4, color, -1)

        # HUD Overlay (Active Track Count)
        hud_text = f"Active Tracks: {len(tracks)}"
        cv2.rectangle(annotated, (8, 8), (170, 38), (20, 5, 35), -1)
        cv2.putText(annotated, hud_text, (14, 30), FONT, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        return annotated


# ---------------------------------------------------------------------------
# IO Helpers
# ---------------------------------------------------------------------------
class VideoSource:
    """Thin wrapper around cv2.VideoCapture with context-manager support."""

    def __init__(self, source: str | int) -> None:
        self._source = source
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> VideoSource:
        self._cap = cv2.VideoCapture(self._source)
        if not self._cap.isOpened():
            raise IOError(f"Cannot open video source: {self._source!r}")
        logger.info(
            "Video opened — source=%s  fps=%.1f  resolution=%dx%d",
            self._source,
            self.fps,
            self.width,
            self.height,
        )
        return self

    def __enter__(self) -> VideoSource:
        return self.open()

    def __exit__(self, *_) -> None:
        self.release()

    def release(self) -> None:
        if self._cap and self._cap.isOpened():
            self._cap.release()

    @property
    def fps(self) -> float:
        return self._cap.get(cv2.CAP_PROP_FPS) or 25.0

    @property
    def width(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def total_frames(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def frames(self) -> Generator[Tuple[int, cv2.Mat], None, None]:
        """Yield (frame_id, frame) pairs — 1-indexed."""
        frame_id = 0
        while True:
            ret, frame = self._cap.read()
            if not ret:
                break
            frame_id += 1
            yield frame_id, frame


class VideoWriter:
    """Wraps cv2.VideoWriter with context-manager support."""

    def __init__(self, path: str, fps: float, width: int, height: int) -> None:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
        if not self._writer.isOpened():
            raise IOError(f"Cannot open video writer at path: {path!r}")
        logger.info("Output video writer opened at %r", path)

    def write(self, frame: cv2.Mat) -> None:
        self._writer.write(frame)

    def release(self) -> None:
        self._writer.release()

    def __enter__(self) -> VideoWriter:
        return self

    def __exit__(self, *_) -> None:
        self.release()


# ---------------------------------------------------------------------------
# Runner Layer
# ---------------------------------------------------------------------------
class TrackingRunner:
    """Orchestrates Phase-2 tracking logic and handles outputs."""

    def __init__(self, config: TrackingConfig) -> None:
        self.config = config
        self.registry = TrackRegistry(config)

    def run(self, source: str | int) -> List[dict]:
        """Run tracking on the given video source end-to-end."""
        logger.info("Loading YOLOv8 model from %s on device %s...", self.config.model_path, self.config.device)
        model = YOLO(self.config.model_path)
        logger.info("Model loaded successfully.")

        all_track_records: List[dict] = []
        writer: VideoWriter | None = None

        with VideoSource(source) as video:
            fps = video.fps
            if self.config.save_output:
                writer = VideoWriter(
                    self.config.output_path,
                    fps,
                    video.width,
                    video.height
                )

            start_time = time.perf_counter()
            frame_count = 0

            try:
                for frame_id, frame in video.frames():
                    if self.config.max_frames and frame_id > self.config.max_frames:
                        logger.info("max_frames limit (%d) reached. Stopping.", self.config.max_frames)
                        break

                    timestamp = round((frame_id - 1) / fps, 2)

                    # Native YOLOv8 built-in ByteTrack
                    # classes=[0] filters results to 'person' only
                    results = model.track(
                        source=frame,
                        persist=True,
                        tracker="bytetrack.yaml",
                        classes=[0],
                        conf=self.config.confidence_threshold,
                        iou=self.config.iou_threshold,
                        device=self.config.device,
                        verbose=False
                    )

                    result = results[0]
                    active_tracks_on_frame = []

                    if result.boxes is not None and result.boxes.id is not None:
                        boxes = result.boxes.xyxy.cpu().numpy()
                        ids = result.boxes.id.cpu().numpy().astype(int).tolist()
                        confs = result.boxes.conf.cpu().numpy()

                        for box, track_id, conf in zip(boxes, ids, confs):
                            x1, y1, x2, y2 = map(int, box)
                            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                            # Register/Update track in registry
                            self.registry.update_track(track_id, frame_id, (cx, cy))

                            # Create record matching the requested format
                            record = {
                                "frame_id": frame_id,
                                "track_id": track_id,
                                "bbox": [x1, y1, x2, y2],
                                "center": [cx, cy],
                                "confidence": round(float(conf), 4),
                                "timestamp": timestamp
                            }
                            active_tracks_on_frame.append(record)
                            all_track_records.append(record)

                    # Visual Annotations
                    if self.config.show_preview or self.config.save_output:
                        annotated = TrackAnnotator.draw(frame, active_tracks_on_frame, self.registry)

                        if writer:
                            writer.write(annotated)

                        if self.config.show_preview:
                            cv2.imshow("Store Intelligence — Person Tracking", annotated)
                            if cv2.waitKey(1) & 0xFF == ord("q"):
                                logger.info("Preview closed by user.")
                                break

                    frame_count += 1

                    if frame_count % 100 == 0:
                        elapsed = time.perf_counter() - start_time
                        logger.info(
                            "Frame %d | %.1f fps | %d active tracks",
                            frame_id,
                            frame_count / elapsed,
                            len(active_tracks_on_frame)
                        )

            finally:
                if writer:
                    writer.release()
                cv2.destroyAllWindows()

        elapsed_total = time.perf_counter() - start_time
        logger.info(
            "Tracking done — %d frames processed in %.2fs (%.1f fps avg)",
            frame_count,
            elapsed_total,
            frame_count / max(elapsed_total, 1e-6)
        )

        return all_track_records


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tracking",
        description="Store Intelligence System — Phase 2: Person Tracking via ByteTrack",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source", required=True,
        help="Video source file path, RTSP stream, or camera index (e.g. 0)"
    )
    parser.add_argument("--model", default="yolov8n.pt", help="YOLOv8 weights file")
    parser.add_argument("--conf", type=float, default=0.50, help="Confidence threshold [0–1]")
    parser.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold [0–1]")
    parser.add_argument("--device", default="cpu", help="Inference device: cpu | 0 | mps")
    parser.add_argument("--preview", action="store_true", help="Show live annotated preview")
    parser.add_argument("--no-save", action="store_true", help="Do not write annotated video to disk")
    parser.add_argument("--output", default="tracked_output.mp4", help="Output video file path")
    parser.add_argument("--tracks-file", default="tracks.json", help="Output tracks JSON file path")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0=all)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # Resolve relative paths to absolute paths to prevent issues with libraries changing CWD
    model_path = args.model
    if isinstance(model_path, str) and Path(model_path).exists():
        model_path = str(Path(model_path).resolve())

    source: str | int = args.source
    if isinstance(source, str):
        if source.isdigit():
            source = int(source)
        elif Path(source).exists():
            source = str(Path(source).resolve())

    output_path = str(Path(args.output).resolve())
    tracks_file = str(Path(args.tracks_file).resolve())

    config = TrackingConfig(
        model_path=model_path,
        confidence_threshold=args.conf,
        iou_threshold=args.iou,
        device=args.device,
        show_preview=args.preview,
        save_output=not args.no_save,
        output_path=output_path,
        tracks_file=tracks_file,
        max_frames=args.max_frames
    )

    runner = TrackingRunner(config=config)
    track_records = runner.run(source=source)

    # Export tracks JSON
    out_path = Path(config.tracks_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(track_records, indent=2), encoding="utf-8")
    logger.info("Track records written to %s", out_path)

    # Export Statistics JSON to console
    stats = runner.registry.get_statistics()
    print("\n--- Tracking Statistics ---")
    print(json.dumps(stats, indent=2))
    print("---------------------------\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
