"""
Store Intelligence System — Phase 4
analytics.py

Consumes tracks.json, events.json, and event_summary.json to calculate store 
traffic analytics and visitor KPIs, and exports them to analytics.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("store_intelligence.analytics")


# ---------------------------------------------------------------------------
# Analytics Engine
# ---------------------------------------------------------------------------
class AnalyticsEngine:
    """Calculates visitor and occupancy analytics from track and event logs."""

    def __init__(self, tracks: List[dict], events: List[dict], summary: dict) -> None:
        self.tracks = tracks
        self.events = events
        self.summary = summary

    def estimate_fps(self) -> float:
        """Estimate the video FPS from frame_ids and timestamps in the records."""
        for r in self.tracks:
            f = r["frame_id"]
            t = r["timestamp"]
            if f > 1 and t > 0:
                return round((f - 1) / t, 1)
        return 30.0  # fallback standard FPS

    def run(self) -> dict:
        """Compute visitor metrics, traffic per minute, and occupancy timeline."""
        fps = self.estimate_fps()

        # 1. Group track records by track_id to analyze durations
        tracks_by_id = defaultdict(list)
        for t in self.tracks:
            tracks_by_id[t["track_id"]].append(t)

        durations = []
        for records in tracks_by_id.values():
            records.sort(key=lambda x: x["frame_id"])
            first_frame = records[0]["frame_id"]
            last_frame = records[-1]["frame_id"]
            duration_s = (last_frame - first_frame) / fps
            durations.append(duration_s)

        # Basic visitor stats
        unique_visitors = len(tracks_by_id)
        avg_visit_duration = round(sum(durations) / unique_visitors, 1) if unique_visitors > 0 else 0.0
        longest_visit_duration = round(max(durations), 1) if unique_visitors > 0 else 0.0

        # 2. Extract stats from event summary
        total_entries = self.summary.get("total_entries", 0)
        total_exits = self.summary.get("total_exits", 0)
        current_occupancy = self.summary.get("current_occupancy", 0)
        peak_occupancy = self.summary.get("peak_occupancy", 0)
        occupancy_timeline = self.summary.get("occupancy_timeline", [])

        # 3. Calculate visitor traffic (entries + exits) per minute
        traffic_per_minute = defaultdict(int)
        for ev in self.events:
            # Extract the minute part "HH:MM" from "YYYY-MM-DDTHH:MM:SS"
            timestamp_str = ev["timestamp"]
            try:
                dt = datetime.fromisoformat(timestamp_str)
                minute_key = dt.strftime("%H:%M")
            except Exception:
                # Fallback string manipulation if datetimes aren't fully standard
                minute_key = timestamp_str.split("T")[1][:5]
            
            traffic_per_minute[minute_key] += 1

        # Sort minute dictionary
        sorted_traffic = {k: traffic_per_minute[k] for k in sorted(traffic_per_minute.keys())}

        # Build final flat KPI structure and charts
        analytics = {
            "total_entries": total_entries,
            "total_exits": total_exits,
            "unique_visitors": unique_visitors,
            "avg_visit_duration": avg_visit_duration,
            "longest_visit_duration": longest_visit_duration,
            "peak_occupancy": peak_occupancy,
            "current_occupancy": current_occupancy,
            "visitor_traffic_per_minute": sorted_traffic,
            "occupancy_over_time": occupancy_timeline
        }

        return analytics


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="analytics",
        description="Store Intelligence System — Phase 4: Analytics Engine",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--tracks", default="tracks.json", help="Path to tracks.json input file")
    parser.add_argument("--events", default="events.json", help="Path to events.json input file")
    parser.add_argument("--summary", default="event_summary.json", help="Path to event_summary.json input file")
    parser.add_argument("--output", default="analytics.json", help="Path to save analytics.json output file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # Resolve paths to absolute paths
    tracks_path = Path(args.tracks).resolve()
    events_path = Path(args.events).resolve()
    summary_path = Path(args.summary).resolve()
    output_path = Path(args.output).resolve()

    # Verify input existence
    for path in (tracks_path, events_path, summary_path):
        if not path.exists():
            logger.error("Required input file not found: %s", path)
            return 1

    # Load input data
    logger.info("Loading inputs: tracks=%s, events=%s, summary=%s", tracks_path.name, events_path.name, summary_path.name)
    with tracks_path.open("r", encoding="utf-8") as f:
        tracks = json.load(f)
    with events_path.open("r", encoding="utf-8") as f:
        events = json.load(f)
    with summary_path.open("r", encoding="utf-8") as f:
        summary = json.load(f)

    # Run analytics calculations
    engine = AnalyticsEngine(tracks, events, summary)
    analytics = engine.run()

    # Export analytics JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(analytics, indent=2), encoding="utf-8")
    logger.info("Analytics metrics exported to %s", output_path)

    # Print summary to console
    print("\n--- Analytics Summary ---")
    print(json.dumps({
        "total_entries": analytics["total_entries"],
        "total_exits": analytics["total_exits"],
        "unique_visitors": analytics["unique_visitors"],
        "avg_visit_duration": analytics["avg_visit_duration"],
        "longest_visit_duration": analytics["longest_visit_duration"],
        "peak_occupancy": analytics["peak_occupancy"],
        "current_occupancy": analytics["current_occupancy"]
    }, indent=2))
    print("-------------------------\n")

    return 0


if __name__ == "__main__":
    from datetime import datetime  # imported inside script main to prevent issues
    sys.exit(main())
