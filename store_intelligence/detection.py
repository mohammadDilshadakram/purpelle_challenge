"""
Store Intelligence System — Phase 1
detection.py

Person detection from CCTV video using YOLOv8.
Clean architecture: configuration, domain models, detector, and runner are
kept in clearly separated layers within this single module.

Usage:
    python detection.py --source path/to/video.mp4
    python detection.py --source 0           # live webcam
    python detection.py --source rtsp://...  # RTSP CCTV stream
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Generator, List

import cv2
from ultralytics import YOLO

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("store_intelligence.detection")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DetectionConfig:
    """Immutable runtime configuration for the person detector."""

    model_path: str = "yolov8n.pt"          # nano is fastest; swap to yolov8m/l for accuracy
    confidence_threshold: float = 0.50       # minimum detection confidence
    iou_threshold: float = 0.45             # NMS IoU threshold
    device: str = "cpu"                     # 'cpu', '0', '0,1', 'mps'
    show_preview: bool = False               # display annotated frames live
    save_output: bool = False                # write annotated video to disk
    output_path: str = "output.mp4"         # path for saved output video
    max_frames: int = 0                     # 0 = process entire source


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------
@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def as_list(self) -> List[int]:
        return [self.x1, self.y1, self.x2, self.y2]

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)


@dataclass
class PersonDetection:
    """
    A single person detection in one video frame.

    Serialised format:
        {
            "frame_id":   1,
            "bbox":       [x1, y1, x2, y2],
            "confidence": 0.91
        }
    """

    frame_id: int
    bbox: BoundingBox
    confidence: float

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "bbox": self.bbox.as_list,
            "confidence": round(self.confidence, 4),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Video Source
# ---------------------------------------------------------------------------
class VideoSource:
    """Thin wrapper around cv2.VideoCapture with context-manager support."""

    def __init__(self, source: str | int) -> None:
        self._source = source
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> "VideoSource":
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

    def __enter__(self) -> "VideoSource":
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

    def frames(self) -> Generator[tuple[int, cv2.Mat], None, None]:
        """Yield (frame_id, frame) pairs — 1-indexed."""
        frame_id = 0
        while True:
            ret, frame = self._cap.read()
            if not ret:
                break
            frame_id += 1
            yield frame_id, frame


# ---------------------------------------------------------------------------
# Person Detector
# ---------------------------------------------------------------------------
class PersonDetector:
    """
    Wraps YOLOv8 and exposes a clean per-frame detection API.

    Only detections belonging to COCO class 0 (person) are returned.
    """

    PERSON_CLASS_ID: int = 0  # COCO class index for 'person'

    def __init__(self, config: DetectionConfig) -> None:
        self.config = config
        self._model: YOLO | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def load(self) -> "PersonDetector":
        logger.info("Loading YOLOv8 model from %r on device %r …", self.config.model_path, self.config.device)
        self._model = YOLO(self.config.model_path)
        logger.info("Model loaded successfully.")
        return self

    # ------------------------------------------------------------------
    # Core Detection
    # ------------------------------------------------------------------
    def detect(self, frame: cv2.Mat, frame_id: int) -> List[PersonDetection]:
        """
        Run inference on a single BGR frame.

        Returns a list of PersonDetection objects (may be empty).
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call .load() first.")

        results = self._model.predict(
            source=frame,
            conf=self.config.confidence_threshold,
            iou=self.config.iou_threshold,
            classes=[self.PERSON_CLASS_ID],
            device=self.config.device,
            verbose=False,
        )

        detections: List[PersonDetection] = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                if class_id != self.PERSON_CLASS_ID:
                    # Defensive guard — should never trigger given classes= filter
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                confidence = float(box.conf[0])

                detections.append(
                    PersonDetection(
                        frame_id=frame_id,
                        bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                        confidence=confidence,
                    )
                )

        return detections

    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------
    @staticmethod
    def draw_bounding_boxes(frame: cv2.Mat, detections: List[PersonDetection]) -> cv2.Mat:
        """
        Draw person bounding boxes onto a copy of *frame*.

        Annotation style:
          • Purple-tinted box with rounded corners (approximated via filled rect)
          • White label bar showing confidence score
          • Person count overlay in the top-left corner
        """
        annotated = frame.copy()
        BOX_COLOR = (180, 80, 255)      # BGR purple-violet
        LABEL_BG  = (50,  10, 80)       # dark purple label background
        TEXT_COLOR = (255, 255, 255)     # white text
        THICKNESS  = 2
        FONT       = cv2.FONT_HERSHEY_SIMPLEX
        FONT_SCALE = 0.55

        for det in detections:
            b = det.bbox
            # Bounding box
            cv2.rectangle(annotated, (b.x1, b.y1), (b.x2, b.y2), BOX_COLOR, THICKNESS)

            # Label background
            label = f"Person  {det.confidence:.0%}"
            (lw, lh), baseline = cv2.getTextSize(label, FONT, FONT_SCALE, 1)
            label_y1 = max(b.y1 - lh - baseline - 6, 0)
            label_y2 = b.y1
            cv2.rectangle(annotated, (b.x1, label_y1), (b.x1 + lw + 8, label_y2), LABEL_BG, -1)

            # Label text
            cv2.putText(
                annotated, label,
                (b.x1 + 4, label_y2 - baseline - 2),
                FONT, FONT_SCALE, TEXT_COLOR, 1, cv2.LINE_AA,
            )

            # Center dot
            cx, cy = b.center
            cv2.circle(annotated, (cx, cy), 3, BOX_COLOR, -1)

        # Person count overlay
        count_text = f"Persons: {len(detections)}"
        cv2.rectangle(annotated, (8, 8), (160, 38), (20, 5, 35), -1)
        cv2.putText(annotated, count_text, (14, 30), FONT, 0.65, TEXT_COLOR, 1, cv2.LINE_AA)

        return annotated


# ---------------------------------------------------------------------------
# Output Writer (optional)
# ---------------------------------------------------------------------------
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

    def __enter__(self) -> "VideoWriter":
        return self

    def __exit__(self, *_) -> None:
        self.release()


# ---------------------------------------------------------------------------
# Detection Runner  (orchestration layer)
# ---------------------------------------------------------------------------
class DetectionRunner:
    """
    Orchestrates video reading, inference, annotation, and result collection.

    Example:
        config = DetectionConfig(model_path="yolov8n.pt", show_preview=True)
        runner = DetectionRunner(config=config)
        all_detections = runner.run(source="store_cctv.mp4")
    """

    def __init__(self, config: DetectionConfig) -> None:
        self.config = config
        self.detector = PersonDetector(config)

    def run(self, source: str | int) -> List[PersonDetection]:
        """
        Process the full video source and return all PersonDetection objects.

        Args:
            source: File path, RTSP URL, or integer camera index.

        Returns:
            A flat list of PersonDetection, one entry per person per frame.
        """
        self.detector.load()

        all_detections: List[PersonDetection] = []
        writer: VideoWriter | None = None

        with VideoSource(source) as video:
            if self.config.save_output:
                writer = VideoWriter(
                    self.config.output_path,
                    video.fps,
                    video.width,
                    video.height,
                )

            start_time = time.perf_counter()
            frame_count = 0

            try:
                for frame_id, frame in video.frames():
                    if self.config.max_frames and frame_id > self.config.max_frames:
                        logger.info("Reached max_frames limit (%d). Stopping.", self.config.max_frames)
                        break

                    # --- Inference ---
                    detections = self.detector.detect(frame, frame_id)
                    all_detections.extend(detections)

                    # --- Annotation ---
                    annotated = self.detector.draw_bounding_boxes(frame, detections)

                    # --- Optional output ---
                    if writer:
                        writer.write(annotated)

                    if self.config.show_preview:
                        cv2.imshow("Store Intelligence — Person Detection", annotated)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            logger.info("Preview window closed by user.")
                            break

                    frame_count += 1

                    if frame_count % 100 == 0:
                        elapsed = time.perf_counter() - start_time
                        logger.info(
                            "Processed %d frames | %.1f fps | %d persons detected so far",
                            frame_count,
                            frame_count / elapsed,
                            len(all_detections),
                        )

            finally:
                if writer:
                    writer.release()
                cv2.destroyAllWindows()

        elapsed_total = time.perf_counter() - start_time
        logger.info(
            "Done — %d frames in %.2fs (%.1f fps avg) | Total person detections: %d",
            frame_count,
            elapsed_total,
            frame_count / max(elapsed_total, 1e-6),
            len(all_detections),
        )

        return all_detections


# ---------------------------------------------------------------------------
# Public API helpers
# ---------------------------------------------------------------------------
def detections_to_json(detections: List[PersonDetection], indent: int = 2) -> str:
    """Serialise a list of PersonDetection objects to a JSON string."""
    return json.dumps([d.to_dict() for d in detections], indent=indent)


def detections_to_jsonl(detections: List[PersonDetection]) -> str:
    """Serialise detections as newline-delimited JSON (streaming-friendly)."""
    return "\n".join(json.dumps(d.to_dict()) for d in detections)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="detection",
        description="Store Intelligence System — Phase 1: Person Detection via YOLOv8",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source", required=True,
        help="Video file path, RTSP URL, or camera index (e.g. 0)",
    )
    parser.add_argument("--model", default="yolov8n.pt", help="YOLOv8 model weights file")
    parser.add_argument("--conf", type=float, default=0.50, help="Confidence threshold [0–1]")
    parser.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold [0–1]")
    parser.add_argument("--device", default="cpu", help="Inference device: cpu | 0 | mps")
    parser.add_argument("--preview", action="store_true", help="Show live annotated preview")
    parser.add_argument("--save", action="store_true", help="Write annotated video to disk")
    parser.add_argument("--output", default="output.mp4", help="Output video file path")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0=all)")
    parser.add_argument(
        "--export", choices=["json", "jsonl", "none"], default="json",
        help="Serialisation format for detection results",
    )
    parser.add_argument("--out-file", default=None, help="Write detections to this file (stdout if omitted)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # Resolve source type
    source: str | int = args.source
    if source.isdigit():
        source = int(source)

    config = DetectionConfig(
        model_path=args.model,
        confidence_threshold=args.conf,
        iou_threshold=args.iou,
        device=args.device,
        show_preview=args.preview,
        save_output=args.save,
        output_path=args.output,
        max_frames=args.max_frames,
    )

    runner = DetectionRunner(config=config)
    detections = runner.run(source=source)

    if args.export == "none":
        return 0

    if args.export == "jsonl":
        payload = detections_to_jsonl(detections)
    else:
        payload = detections_to_json(detections)

    if args.out_file:
        out_path = Path(args.out_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
        logger.info("Detections written to %s", out_path)
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
