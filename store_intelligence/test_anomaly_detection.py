"""
Unit and Integration Tests for anomaly_detection.py
"""

import json
import sqlite3
import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from store_intelligence.anomaly_detection import (
    init_db,
    store_anomalies,
    get_anomalies,
    CrowdFormationDetector,
    ExcessiveLoiteringDetector,
    TrafficSpikeDetector,
    AnomalyDetectionPipeline,
    main
)


class TestDatabaseOperations(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = Path(self.temp_db_file.name)
        self.temp_db_file.close()

    def tearDown(self) -> None:
        if self.temp_db_path.exists():
            self.temp_db_path.unlink()

    def test_init_db_creates_table(self) -> None:
        init_db(self.temp_db_path)
        
        # Verify tables
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='anomalies'")
        table = cursor.fetchone()
        self.assertIsNotNone(table)
        conn.close()

    def test_store_anomalies_and_duplicates(self) -> None:
        init_db(self.temp_db_path)
        
        anomalies = [
            {"type": "crowding", "severity": "high", "timestamp": "2026-04-10T12:15:22"},
            {"type": "loitering", "person_id": 15, "duration_seconds": 1250},
            {"type": "traffic_spike", "severity": "medium", "timestamp": "2026-04-10T12:17:00"}
        ]
        
        # Initial store
        store_anomalies(self.temp_db_path, anomalies)
        
        # Double store to test duplicate prevention
        store_anomalies(self.temp_db_path, anomalies)
        
        # Verify count
        stats = get_anomalies(self.temp_db_path)
        self.assertEqual(stats["total_anomalies"], 3)
        self.assertEqual(stats["crowding"], 1)
        self.assertEqual(stats["loitering"], 1)
        self.assertEqual(stats["traffic_spikes"], 1)


class TestAnomalyDetectors(unittest.TestCase):
    def test_crowd_formation_detector(self) -> None:
        config = {"threshold": 2, "duration": 10}
        detector = CrowdFormationDetector(config)
        
        # 12:10:00 - occupancy 1
        # 12:10:05 - occupancy 3 (exceeds threshold)
        # 12:10:20 - occupancy 3 (duration = 15s > 10s)
        # 12:10:21 - occupancy 1 (crowding ends)
        events = [
            {"timestamp": "2026-04-10T12:10:00", "event": "entry"}, # 1
            {"timestamp": "2026-04-10T12:10:05", "event": "entry"}, # 2
            {"timestamp": "2026-04-10T12:10:05", "event": "entry"}, # 3 (exceeds)
            {"timestamp": "2026-04-10T12:10:21", "event": "exit"}    # 2 (ends)
        ]
        
        anomalies = detector.detect(tracks=[], events=events, analytics={})
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["type"], "crowding")
        self.assertEqual(anomalies[0]["severity"], "high")
        self.assertEqual(anomalies[0]["timestamp"], "2026-04-10T12:10:05")

    def test_excessive_loitering_detector(self) -> None:
        config = {"threshold_seconds": 100}
        detector = ExcessiveLoiteringDetector(config)
        
        # Method A: tracks
        tracks = [
            {"track_id": 1, "timestamp": 0.0, "frame_id": 1},
            {"track_id": 1, "timestamp": 120.0, "frame_id": 4000}, # duration 120s > 100s
            {"track_id": 2, "timestamp": 0.0, "frame_id": 1},
            {"track_id": 2, "timestamp": 50.0, "frame_id": 1600}   # duration 50s <= 100s
        ]
        
        anomalies = detector.detect(tracks=tracks, events=[], analytics={})
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["type"], "loitering")
        self.assertEqual(anomalies[0]["person_id"], 1)
        self.assertEqual(anomalies[0]["duration_seconds"], 120)
        
        # Method B: events
        events = [
            {"person_id": 3, "timestamp": "2026-04-10T12:10:00", "event": "entry"},
            {"person_id": 3, "timestamp": "2026-04-10T12:13:00", "event": "exit"} # duration 180s > 100s
        ]
        anomalies = detector.detect(tracks=[], events=events, analytics={})
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["type"], "loitering")
        self.assertEqual(anomalies[0]["person_id"], 3)
        self.assertEqual(anomalies[0]["duration_seconds"], 180)

    def test_traffic_spike_detector(self) -> None:
        config = {
            "window_seconds": 10,
            "rolling_average_windows": 3,
            "threshold_multiplier": 2.0
        }
        detector = TrafficSpikeDetector(config)
        
        # Entries:
        # Window 0 (12:00:00 - 12:00:10): 2 entries
        # Window 1 (12:00:10 - 12:00:20): 2 entries
        # Window 2 (12:00:20 - 12:00:30): 2 entries
        # Window 3 (12:00:30 - 12:00:40): 6 entries (rolling average of previous 3 was 2. Spike!)
        events = [
            # Window 0
            {"timestamp": "2026-04-10T12:00:01", "event": "entry"},
            {"timestamp": "2026-04-10T12:00:05", "event": "entry"},
            # Window 1
            {"timestamp": "2026-04-10T12:00:12", "event": "entry"},
            {"timestamp": "2026-04-10T12:00:18", "event": "entry"},
            # Window 2
            {"timestamp": "2026-04-10T12:00:22", "event": "entry"},
            {"timestamp": "2026-04-10T12:00:27", "event": "entry"},
            # Window 3
            {"timestamp": "2026-04-10T12:00:31", "event": "entry"},
            {"timestamp": "2026-04-10T12:00:32", "event": "entry"},
            {"timestamp": "2026-04-10T12:00:33", "event": "entry"},
            {"timestamp": "2026-04-10T12:00:34", "event": "entry"},
            {"timestamp": "2026-04-10T12:00:35", "event": "entry"},
            {"timestamp": "2026-04-10T12:00:36", "event": "entry"}
        ]
        
        anomalies = detector.detect(tracks=[], events=events, analytics={})
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["type"], "traffic_spike")
        self.assertEqual(anomalies[0]["severity"], "medium")


class TestPipelineIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)
        
        # Write mock files
        self.tracks_file = self.dir_path / "tracks.json"
        self.events_file = self.dir_path / "events.json"
        self.analytics_file = self.dir_path / "analytics.json"
        self.db_file = self.dir_path / "anomalies.db"
        self.output_file = self.dir_path / "anomalies.json"
        
        # Create some loitering & traffic spike mock data
        # Track 1 lasts 100 seconds (loitering threshold set to 50)
        tracks_data = [
            {"track_id": 1, "timestamp": 0.0, "frame_id": 1, "center": [100, 100]},
            {"track_id": 1, "timestamp": 100.0, "frame_id": 3000, "center": [102, 100]}
        ]
        # Spike in minute 1
        events_data = [
            {"person_id": 1, "timestamp": "2026-04-10T12:10:05", "event": "entry", "track_duration": 100.0},
            {"person_id": 2, "timestamp": "2026-04-10T12:11:05", "event": "entry", "track_duration": 10.0},
            {"person_id": 3, "timestamp": "2026-04-10T12:11:06", "event": "entry", "track_duration": 10.0},
            {"person_id": 4, "timestamp": "2026-04-10T12:11:07", "event": "entry", "track_duration": 10.0}
        ]
        analytics_data = {}
        
        self.tracks_file.write_text(json.dumps(tracks_data), encoding="utf-8")
        self.events_file.write_text(json.dumps(events_data), encoding="utf-8")
        self.analytics_file.write_text(json.dumps(analytics_data), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_pipeline_execution(self) -> None:
        argv = [
            "--tracks", str(self.tracks_file),
            "--events", str(self.events_file),
            "--analytics", str(self.analytics_file),
            "--db", str(self.db_file),
            "--output", str(self.output_file),
            "--loiter-threshold", "50",
            "--spike-multiplier", "1.5"
        ]
        
        exit_code = main(argv)
        self.assertEqual(exit_code, 0)
        
        # Verify db created
        self.assertTrue(self.db_file.exists())
        
        # Verify JSON file created
        self.assertTrue(self.output_file.exists())
        
        # Verify output structure
        with self.output_file.open("r", encoding="utf-8") as f:
            anomalies = json.load(f)
            self.assertGreater(len(anomalies), 0)
            
        stats = get_anomalies(self.db_file)
        self.assertGreater(stats["total_anomalies"], 0)


if __name__ == "__main__":
    unittest.main()
