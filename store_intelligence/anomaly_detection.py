"""
Store Intelligence System — Phase 5
anomaly_detection.py

Detects operational anomalies from tracking and event data.
Supports extensible anomaly detection using the Strategy Pattern.
Saves anomalies to SQLite and exports to anomalies.json.
Provides helper function get_anomalies() to return summary statistics.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Type, Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("store_intelligence.anomaly_detection")


# ---------------------------------------------------------------------------
# Database Layer
# ---------------------------------------------------------------------------
def init_db(db_path: str | Path) -> None:
    """Initialize the SQLite database schema if it does not exist."""
    db_path = Path(db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                severity TEXT,
                timestamp TEXT,
                person_id INTEGER,
                duration_seconds INTEGER,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def store_anomalies(db_path: str | Path, anomalies: List[dict]) -> None:
    """Store list of anomalies in SQLite database, avoiding duplicates."""
    db_path = Path(db_path).resolve()
    init_db(db_path)
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        for anomaly in anomalies:
            atype = anomaly.get("type")
            severity = anomaly.get("severity")
            timestamp = anomaly.get("timestamp")
            person_id = anomaly.get("person_id")
            duration_seconds = anomaly.get("duration_seconds")
            
            # Extract any remaining fields into details JSON
            standard_keys = {"type", "severity", "timestamp", "person_id", "duration_seconds"}
            details_dict = {k: v for k, v in anomaly.items() if k not in standard_keys}
            details = json.dumps(details_dict) if details_dict else None
            
            # Check for duplicate: same type, timestamp, person_id, duration_seconds
            cursor.execute("""
                SELECT id FROM anomalies 
                WHERE type = ? 
                  AND (timestamp = ? OR (timestamp IS NULL AND ? IS NULL))
                  AND (person_id = ? OR (person_id IS NULL AND ? IS NULL))
                  AND (duration_seconds = ? OR (duration_seconds IS NULL AND ? IS NULL))
            """, (atype, timestamp, timestamp, person_id, person_id, duration_seconds, duration_seconds))
            
            if cursor.fetchone() is None:
                cursor.execute("""
                    INSERT INTO anomalies (type, severity, timestamp, person_id, duration_seconds, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (atype, severity, timestamp, person_id, duration_seconds, details))
        conn.commit()
    finally:
        conn.close()


def get_anomalies(db_path: str | Path = "anomalies.db") -> dict:
    """
    Helper function to query anomalies from SQLite and generate summary statistics.
    
    Returns:
        dict: {
            "total_anomalies": int,
            "crowding": int,
            "loitering": int,
            "traffic_spikes": int
        }
    """
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        return {
            "total_anomalies": 0,
            "crowding": 0,
            "loitering": 0,
            "traffic_spikes": 0
        }
        
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Query total count
        cursor.execute("SELECT COUNT(*) FROM anomalies")
        total_anomalies = cursor.fetchone()[0]
        
        # Query specific counts
        cursor.execute("SELECT COUNT(*) FROM anomalies WHERE type = 'crowding'")
        crowding = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM anomalies WHERE type = 'loitering'")
        loitering = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM anomalies WHERE type = 'traffic_spike'")
        traffic_spikes = cursor.fetchone()[0]
        
        return {
            "total_anomalies": total_anomalies,
            "crowding": crowding,
            "loitering": loitering,
            "traffic_spikes": traffic_spikes
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Anomaly Detector Strategy Pattern
# ---------------------------------------------------------------------------
class BaseAnomalyDetector:
    """Base class for all anomaly detectors. Inherit to support future anomaly types."""
    
    def __init__(self, config: dict = None) -> None:
        self.config = config or {}

    def detect(self, tracks: List[dict], events: List[dict], analytics: dict) -> List[dict]:
        """
        Analyze logs and return a list of anomaly dictionaries.
        
        Args:
            tracks (list): Raw track records from tracks.json.
            events (list): Raw entry/exit events from events.json.
            analytics (dict): Analytics KPIs from analytics.json.
            
        Returns:
            list[dict]: List of detected anomalies.
        """
        raise NotImplementedError("Detectors must implement detect()")


class CrowdFormationDetector(BaseAnomalyDetector):
    """
    Anomaly Type 1: Crowd Formation
    Detects if occupancy exceeds threshold for more than N seconds.
    """
    
    def detect(self, tracks: List[dict], events: List[dict], analytics: dict) -> List[dict]:
        threshold = self.config.get("threshold", 15)
        duration_limit = self.config.get("duration", 30)
        severity = self.config.get("severity", "high")
        
        # Step 1: Build occupancy timeline
        timeline: List[Tuple[datetime, int]] = []
        
        if events:
            # Reconstruct timeline from events in events.json
            sorted_events = sorted(events, key=lambda e: e.get("timestamp", ""))
            occupancy = 0
            for ev in sorted_events:
                timestamp_str = ev.get("timestamp")
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError):
                    continue
                    
                if ev.get("event") == "entry":
                    occupancy += 1
                elif ev.get("event") == "exit":
                    occupancy = max(0, occupancy - 1)
                    
                timeline.append((dt, occupancy))
        elif tracks:
            # Fallback: Estimate timeline using track density per timestamp
            tracks_by_time = defaultdict(set)
            for t in tracks:
                timestamp_val = t.get("timestamp", 0.0)
                track_id = t.get("track_id")
                tracks_by_time[timestamp_val].add(track_id)
                
            base_time = datetime.fromisoformat(self.config.get("base_time", "2026-04-10T12:10:00"))
            for ts, track_ids in sorted(tracks_by_time.items()):
                dt = base_time + timedelta(seconds=ts)
                timeline.append((dt, len(track_ids)))
        else:
            # Fallback 2: Check timeline inside analytics.json if available
            occupancy_over_time = analytics.get("occupancy_over_time", [])
            base_date_str = self.config.get("base_date", "2026-04-10T")
            for item in occupancy_over_time:
                time_str = item.get("time")  # e.g., "12:10:31"
                occ = item.get("occupancy", 0)
                try:
                    dt = datetime.fromisoformat(base_date_str + time_str)
                    timeline.append((dt, occ))
                except (ValueError, TypeError):
                    continue
        
        if not timeline:
            return []
            
        # Step 2: Identify continuous crowding intervals
        anomalies = []
        crowding_start: datetime | None = None
        
        for i, (dt, occ) in enumerate(timeline):
            if occ > threshold:
                if crowding_start is None:
                    crowding_start = dt
            else:
                if crowding_start is not None:
                    # Crowding interval ended
                    duration = (dt - crowding_start).total_seconds()
                    if duration > duration_limit:
                        anomalies.append({
                            "type": "crowding",
                            "severity": severity,
                            "timestamp": crowding_start.strftime("%Y-%m-%dT%H:%M:%S")
                        })
                    crowding_start = None
                    
        # Check if crowding is ongoing at the end of the timeline
        if crowding_start is not None:
            last_dt = timeline[-1][0]
            duration = (last_dt - crowding_start).total_seconds()
            if duration > duration_limit:
                anomalies.append({
                    "type": "crowding",
                    "severity": severity,
                    "timestamp": crowding_start.strftime("%Y-%m-%dT%H:%M:%S")
                })
                
        return anomalies


class ExcessiveLoiteringDetector(BaseAnomalyDetector):
    """
    Anomaly Type 2: Excessive Loitering
    Detects if a visitor remains inside store longer than configurable threshold.
    """
    
    def detect(self, tracks: List[dict], events: List[dict], analytics: dict) -> List[dict]:
        threshold_seconds = self.config.get("threshold_seconds", 900)  # default 15 mins (900s)
        
        loiterers: Dict[int, float] = {}  # person_id -> duration
        
        # Method A: Process tracks.json for direct track durations
        if tracks:
            tracks_by_id = defaultdict(list)
            for t in tracks:
                tracks_by_id[t.get("track_id")].append(t)
                
            for track_id, records in tracks_by_id.items():
                records.sort(key=lambda x: x.get("frame_id", 0))
                first_ts = records[0].get("timestamp", 0.0)
                last_ts = records[-1].get("timestamp", 0.0)
                duration = last_ts - first_ts
                if duration > threshold_seconds:
                    loiterers[track_id] = max(loiterers.get(track_id, 0.0), duration)
                    
        # Method B: Process events.json for entries and exits
        if events:
            # Track durations are directly populated in events
            for ev in events:
                person_id = ev.get("person_id")
                track_dur = ev.get("track_duration", 0.0)
                if track_dur > threshold_seconds:
                    loiterers[person_id] = max(loiterers.get(person_id, 0.0), track_dur)
                    
            # Calculate time between entry and exit events as a second layer
            events_by_person = defaultdict(list)
            for ev in events:
                person_id = ev.get("person_id")
                events_by_person[person_id].append(ev)
                
            for person_id, p_events in events_by_person.items():
                p_events.sort(key=lambda e: e.get("timestamp", ""))
                entry_dt: datetime | None = None
                for ev in p_events:
                    e_type = ev.get("event")
                    timestamp_str = ev.get("timestamp")
                    try:
                        dt = datetime.fromisoformat(timestamp_str)
                    except (ValueError, TypeError):
                        continue
                        
                    if e_type == "entry":
                        entry_dt = dt
                    elif e_type == "exit" and entry_dt is not None:
                        duration = (dt - entry_dt).total_seconds()
                        if duration > threshold_seconds:
                            loiterers[person_id] = max(loiterers.get(person_id, 0.0), duration)
                        entry_dt = None
                        
        anomalies = []
        for person_id, duration in sorted(loiterers.items()):
            anomalies.append({
                "type": "loitering",
                "person_id": person_id,
                "duration_seconds": int(duration)
            })
            
        return anomalies


class TrafficSpikeDetector(BaseAnomalyDetector):
    """
    Anomaly Type 3: Traffic Spike
    Detects if visitor count during a time window exceeds rolling average by configurable percentage.
    """
    
    def detect(self, tracks: List[dict], events: List[dict], analytics: dict) -> List[dict]:
        window_seconds = self.config.get("window_seconds", 60)
        rolling_count = self.config.get("rolling_average_windows", 5)
        multiplier = self.config.get("threshold_multiplier", 2.0)  # > 200% of rolling avg
        severity = self.config.get("severity", "medium")
        
        # Step 1: Collect arrival timestamps
        arrival_times: List[datetime] = []
        
        if events:
            # Use entry event timestamps
            for ev in events:
                if ev.get("event") == "entry":
                    try:
                        arrival_times.append(datetime.fromisoformat(ev.get("timestamp")))
                    except (ValueError, TypeError):
                        continue
        elif tracks:
            # Use first seen timestamp for each track_id
            first_seen_by_track = {}
            for t in tracks:
                track_id = t.get("track_id")
                ts = t.get("timestamp", 0.0)
                if track_id not in first_seen_by_track or ts < first_seen_by_track[track_id]:
                    first_seen_by_track[track_id] = ts
                    
            base_time = datetime.fromisoformat(self.config.get("base_time", "2026-04-10T12:10:00"))
            for ts in first_seen_by_track.values():
                arrival_times.append(base_time + timedelta(seconds=ts))
        else:
            # Check visitor traffic per minute from analytics.json as fallback
            traffic_per_min = analytics.get("visitor_traffic_per_minute", {})
            if traffic_per_min:
                base_date_str = self.config.get("base_date", "2026-04-10T")
                counts = []
                for time_str, count in sorted(traffic_per_min.items()):
                    counts.append(count)
                
                # Check for spikes on pre-aggregated minutes
                anomalies = []
                for i in range(1, len(counts)):
                    prev_counts = counts[max(0, i - rolling_count):i]
                    avg = sum(prev_counts) / len(prev_counts)
                    if avg > 0 and counts[i] > avg * multiplier:
                        anomalies.append({
                            "type": "traffic_spike",
                            "severity": severity
                        })
                return anomalies
                
        if not arrival_times:
            return []
            
        arrival_times.sort()
        start_time = arrival_times[0]
        end_time = arrival_times[-1]
        
        total_span = (end_time - start_time).total_seconds()
        num_windows = int(total_span // window_seconds) + 1
        
        # Step 2: Bucket entries into windows
        window_counts = [0] * num_windows
        for dt in arrival_times:
            seconds_diff = (dt - start_time).total_seconds()
            window_idx = int(seconds_diff // window_seconds)
            if 0 <= window_idx < num_windows:
                window_counts[window_idx] += 1
                
        # Step 3: Run rolling average comparison
        anomalies = []
        for i in range(1, num_windows):
            prev_windows = window_counts[max(0, i - rolling_count):i]
            avg_traffic = sum(prev_windows) / len(prev_windows)
            
            if avg_traffic > 0 and window_counts[i] > avg_traffic * multiplier:
                anomalies.append({
                    "type": "traffic_spike",
                    "severity": severity
                })
                
        return anomalies


# Detector registry for Strategy pattern
DETECTOR_REGISTRY: Dict[str, Type[BaseAnomalyDetector]] = {
    "crowding": CrowdFormationDetector,
    "loitering": ExcessiveLoiteringDetector,
    "traffic_spike": TrafficSpikeDetector
}


# ---------------------------------------------------------------------------
# Pipeline Runner
# ---------------------------------------------------------------------------
class AnomalyDetectionPipeline:
    """Orchestrates anomaly detection strategy execution and exports outputs."""
    
    def __init__(self, config: dict) -> None:
        self.config = config
        self.detectors: List[BaseAnomalyDetector] = []
        
        # Instantiate registered detectors based on config
        detectors_config = config.get("detectors", {})
        for name, cls in DETECTOR_REGISTRY.items():
            detector_cfg = detectors_config.get(name, {})
            # Make sure general configs are available
            detector_cfg.update({
                "base_time": config.get("base_time", "2026-04-10T12:10:00"),
                "base_date": config.get("base_date", "2026-04-10T")
            })
            self.detectors.append(cls(config=detector_cfg))

    def run(self, tracks_path: Path, events_path: Path, analytics_path: Path, funnel_path: Path | None = None) -> List[dict]:
        """Execute detection pipeline on all input files."""
        tracks = []
        events = []
        analytics = {}
        
        # Load files safely
        if tracks_path.exists():
            with tracks_path.open("r", encoding="utf-8") as f:
                try:
                    tracks = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Failed to decode tracks JSON.")
        
        if events_path.exists():
            with events_path.open("r", encoding="utf-8") as f:
                try:
                    events = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Failed to decode events JSON.")
                    
        if analytics_path.exists():
            with analytics_path.open("r", encoding="utf-8") as f:
                try:
                    analytics = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Failed to decode analytics JSON.")

        # If a future anomaly type depends on funnel.json, we can load it here
        funnel = {}
        if funnel_path and funnel_path.exists():
            with funnel_path.open("r", encoding="utf-8") as f:
                try:
                    funnel = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Failed to decode funnel JSON.")

        all_anomalies = []
        for detector in self.detectors:
            try:
                detected = detector.detect(tracks, events, analytics)
                all_anomalies.extend(detected)
            except Exception as e:
                logger.error("Error running detector %s: %s", detector.__class__.__name__, e, exc_info=True)
                
        return all_anomalies


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anomaly_detection",
        description="Store Intelligence System — Phase 5: Anomaly Detection Engine",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--tracks", default="store_intelligence/tracks.json", help="Path to tracks.json")
    parser.add_argument("--events", default="store_intelligence/events.json", help="Path to events.json")
    parser.add_argument("--analytics", default="store_intelligence/analytics.json", help="Path to analytics.json")
    parser.add_argument("--funnel", default="store_intelligence/funnel.json", help="Path to funnel.json (optional)")
    parser.add_argument("--db", default="store_intelligence/anomalies.db", help="SQLite database path")
    parser.add_argument("--output", default="store_intelligence/anomalies.json", help="Export anomalies JSON path")
    
    # Threshold CLI parameters
    parser.add_argument("--crowd-threshold", type=int, default=15, help="Crowd threshold (people)")
    parser.add_argument("--crowd-duration", type=int, default=30, help="Crowd duration (seconds)")
    parser.add_argument("--loiter-threshold", type=int, default=900, help="Loitering threshold (seconds)")
    parser.add_argument("--spike-multiplier", type=float, default=2.0, help="Spike rolling average multiplier")
    parser.add_argument("--base-time", default="2026-04-10T12:10:00", help="Base time for timestamp mapping")
    
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    
    # Build config dictionary
    config = {
        "db_path": args.db,
        "output_json": args.output,
        "base_time": args.base_time,
        "detectors": {
            "crowding": {
                "threshold": args.crowd_threshold,
                "duration": args.crowd_duration,
                "severity": "high"
            },
            "loitering": {
                "threshold_seconds": args.loiter_threshold
            },
            "traffic_spike": {
                "threshold_multiplier": args.spike_multiplier,
                "severity": "medium"
            }
        }
    }
    
    # Paths
    tracks_path = Path(args.tracks).resolve()
    events_path = Path(args.events).resolve()
    analytics_path = Path(args.analytics).resolve()
    funnel_path = Path(args.funnel).resolve() if args.funnel else None
    db_path = Path(args.db).resolve()
    output_path = Path(args.output).resolve()
    
    # Run pipeline
    pipeline = AnomalyDetectionPipeline(config)
    logger.info("Running Anomaly Detection Pipeline...")
    anomalies = pipeline.run(tracks_path, events_path, analytics_path, funnel_path)
    
    logger.info("Found %d anomalies.", len(anomalies))
    
    # Store in database
    store_anomalies(db_path, anomalies)
    logger.info("Anomalies stored in SQLite database at: %s", db_path)
    
    # Export JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(anomalies, indent=2), encoding="utf-8")
    logger.info("Anomalies exported to: %s", output_path)
    
    # Summary
    stats = get_anomalies(db_path)
    print("\n--- Anomaly Statistics Summary ---")
    print(json.dumps(stats, indent=2))
    print("----------------------------------\n")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
