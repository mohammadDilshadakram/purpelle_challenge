"""
Integration Tests for app/api.py
"""

import unittest
from fastapi.testclient import TestClient

from app.api import app


class TestFastAPIBackend(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0")

    def test_metrics_endpoint(self) -> None:
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_entries", data)
        self.assertIn("total_exits", data)
        self.assertIn("unique_visitors", data)
        self.assertIn("peak_occupancy", data)
        self.assertIn("avg_visit_duration", data)

    def test_funnel_endpoint(self) -> None:
        response = self.client.get("/funnel")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_passersby", data)
        self.assertIn("entered_store", data)
        self.assertIn("browsed_aisle", data)
        self.assertIn("checkout", data)
        self.assertIn("conversion_rates", data)
        self.assertIn("entry_rate", data["conversion_rates"])
        self.assertIn("browse_rate", data["conversion_rates"])
        self.assertIn("purchase_rate", data["conversion_rates"])

    def test_anomalies_endpoint(self) -> None:
        response = self.client.get("/anomalies")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("summary", data)
        self.assertIn("anomalies", data)
        self.assertIn("total_anomalies", data["summary"])
        self.assertIn("crowding", data["summary"])
        self.assertIn("loitering", data["summary"])
        self.assertIn("traffic_spikes", data["summary"])

    def test_occupancy_endpoint(self) -> None:
        response = self.client.get("/occupancy")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("timeline", data)

    def test_visitors_endpoint(self) -> None:
        response = self.client.get("/visitors")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_visitors", data)
        self.assertIn("avg_duration", data)
        self.assertIn("longest_duration", data)
        self.assertIn("visitors", data)


    def test_versioned_v1_endpoints(self) -> None:
        # Test /api/v1 prefix
        for endpoint in ["health", "metrics", "funnel", "anomalies", "occupancy", "visitors"]:
            response = self.client.get(f"/api/v1/{endpoint}")
            self.assertEqual(response.status_code, 200, f"Failed on /api/v1/{endpoint}")
            
        # Test /v1 prefix
        for endpoint in ["health", "metrics", "funnel", "anomalies", "occupancy", "visitors"]:
            response = self.client.get(f"/v1/{endpoint}")
            self.assertEqual(response.status_code, 200, f"Failed on /v1/{endpoint}")


if __name__ == "__main__":
    unittest.main()

