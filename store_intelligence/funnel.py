"""
Store Intelligence System — Phase 6
funnel.py

Consumes tracks.json and events.json to calculate the visitor checkout conversion funnel,
and exports the metrics to funnel.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("store_intelligence.funnel")


# ---------------------------------------------------------------------------
# Funnel Engine
# ---------------------------------------------------------------------------
class FunnelEngine:
    """Calculates conversion funnel statistics from track and event logs."""

    def __init__(self, tracks: List[dict], events: List[dict]) -> None:
        self.tracks = tracks
        self.events = events

    def run(self) -> dict:
        """Compute conversion funnel and rates."""
        # 1. Total passersby is unique track IDs from tracks.json
        track_ids = {t["track_id"] for t in self.tracks if "track_id" in t}
        total_passersby = len(track_ids)

        # 2. Entered store is unique person_ids with an 'entry' event in events.json
        entered_visitors = {
            ev["person_id"] for ev in self.events 
            if ev.get("event") == "entry" and "person_id" in ev
        }
        entered_store = len(entered_visitors)

        # 3. Browsed aisle is unique person_ids with track_duration > 10.0 seconds
        browsed_visitors = {
            ev["person_id"] for ev in self.events
            if ev.get("track_duration", 0.0) > 10.0 and "person_id" in ev
        }
        browsed_aisle = len(browsed_visitors)

        # 4. Checkout is unique person_ids with track_duration > 20.0 seconds
        checkout_visitors = {
            ev["person_id"] for ev in self.events
            if ev.get("track_duration", 0.0) > 20.0 and "person_id" in ev
        }
        checkout = len(checkout_visitors)

        # Calculate conversion rates
        entry_rate = round(entered_store / total_passersby, 3) if total_passersby > 0 else 0.0
        browse_rate = round(browsed_aisle / entered_store, 3) if entered_store > 0 else 0.0
        purchase_rate = round(checkout / entered_store, 3) if entered_store > 0 else 0.0

        funnel_data = {
            "total_passersby": total_passersby,
            "entered_store": entered_store,
            "browsed_aisle": browsed_aisle,
            "checkout": checkout,
            "conversion_rates": {
                "entry_rate": entry_rate,
                "browse_rate": browse_rate,
                "purchase_rate": purchase_rate
            }
        }

        return funnel_data


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="funnel",
        description="Store Intelligence System — Phase 6: Conversion Funnel Engine",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--tracks", default="store_intelligence/tracks.json", help="Path to tracks.json input file")
    parser.add_argument("--events", default="store_intelligence/events.json", help="Path to events.json input file")
    parser.add_argument("--output", default="store_intelligence/funnel.json", help="Path to save funnel.json output file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    tracks_path = Path(args.tracks).resolve()
    events_path = Path(args.events).resolve()
    output_path = Path(args.output).resolve()

    # Verify inputs
    for path in (tracks_path, events_path):
        if not path.exists():
            logger.error("Required input file not found: %s", path)
            return 1

    logger.info("Loading inputs: tracks=%s, events=%s", tracks_path.name, events_path.name)
    with tracks_path.open("r", encoding="utf-8") as f:
        tracks = json.load(f)
    with events_path.open("r", encoding="utf-8") as f:
        events = json.load(f)

    # Run funnel calculations
    engine = FunnelEngine(tracks, events)
    funnel_data = engine.run()

    # Export output JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(funnel_data, indent=2), encoding="utf-8")
    logger.info("Funnel metrics exported to %s", output_path)

    # Print summary to console
    print("\n--- Funnel Summary ---")
    print(json.dumps(funnel_data, indent=2))
    print("----------------------\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
