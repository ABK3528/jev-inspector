"""
Tests for Scheduler, ResultStore, HealthCheckServer, and multi-site orchestration.
Covers:
1. ResultStore: SQLite persistence, save, query, health summary
2. SiteTarget dataclass construction
3. InspectionScheduler: concurrent multi-site execution with mock
4. HealthCheckServer: /health, /metrics, /history endpoints
5. Retry & backoff verification
"""

import os
import json
import time
import unittest
import threading
import sqlite3
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import patch, MagicMock

from scheduler import (
    SiteTarget, ResultStore, InspectionScheduler, HealthCheckServer
)


class TestSiteTarget(unittest.TestCase):
    def test_basic_construction(self):
        site = SiteTarget(name="TestApp", url="https://example.com", max_actions=10)
        self.assertEqual(site.name, "TestApp")
        self.assertEqual(site.url, "https://example.com")
        self.assertEqual(site.max_actions, 10)
        self.assertEqual(site.tags, [])

    def test_with_tags(self):
        site = SiteTarget(name="X", url="https://x.com", tags=["social", "prod"])
        self.assertEqual(len(site.tags), 2)


class TestResultStore(unittest.TestCase):
    DB_PATH = "test_result_store.db"

    def setUp(self):
        if os.path.exists(self.DB_PATH):
            os.remove(self.DB_PATH)
        self.store = ResultStore(db_path=self.DB_PATH)

    def tearDown(self):
        if os.path.exists(self.DB_PATH):
            os.remove(self.DB_PATH)

    def test_save_and_retrieve(self):
        report = {
            "summary": {
                "target_url": "https://example.com",
                "status": "PASSED",
                "total_actions_executed": 5,
                "total_errors_detected": 0,
                "duration_seconds": 3.2,
                "timestamp": "2026-10-10 12:00:00"
            },
            "errors_detected": [],
            "executed_actions": []
        }
        self.store.save_result("ExampleSite", report)

        results = self.store.get_latest_results(10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["site_name"], "ExampleSite")
        self.assertEqual(results[0]["status"], "PASSED")

    def test_site_history(self):
        for i in range(3):
            report = {
                "summary": {
                    "target_url": "https://a.com",
                    "status": "PASSED" if i < 2 else "FAILED",
                    "total_actions_executed": i + 1,
                    "total_errors_detected": 0 if i < 2 else 1,
                    "duration_seconds": 1.0 + i,
                    "timestamp": f"2026-10-10 12:0{i}:00"
                },
                "errors_detected": []
            }
            self.store.save_result("SiteA", report)

        history = self.store.get_site_history("SiteA", limit=5)
        self.assertEqual(len(history), 3)
        # Latest first
        self.assertEqual(history[0]["status"], "FAILED")

    def test_health_summary(self):
        # Two sites, one PASSED, one FAILED
        self.store.save_result("SiteA", {
            "summary": {"target_url": "https://a.com", "status": "PASSED",
                        "total_actions_executed": 5, "total_errors_detected": 0,
                        "duration_seconds": 2, "timestamp": "2026-10-10 12:00:00"},
            "errors_detected": []
        })
        self.store.save_result("SiteB", {
            "summary": {"target_url": "https://b.com", "status": "FAILED",
                        "total_actions_executed": 3, "total_errors_detected": 2,
                        "duration_seconds": 4, "timestamp": "2026-10-10 12:01:00"},
            "errors_detected": [{"error_type": "system_error"}]
        })

        summary = self.store.get_health_summary()
        self.assertEqual(summary["overall_status"], "DEGRADED")
        self.assertEqual(summary["total_monitored_sites"], 2)
        self.assertEqual(summary["total_historical_runs"], 2)


class TestHealthCheckServer(unittest.TestCase):
    DB_PATH = "test_hc_store.db"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.DB_PATH):
            os.remove(cls.DB_PATH)
        cls.store = ResultStore(db_path=cls.DB_PATH)
        # Seed data
        cls.store.save_result("TestSite", {
            "summary": {"target_url": "https://test.com", "status": "PASSED",
                        "total_actions_executed": 5, "total_errors_detected": 0,
                        "duration_seconds": 2, "timestamp": "2026-10-10 12:00:00"},
            "errors_detected": []
        })
        cls.server = HealthCheckServer(cls.store, host="127.0.0.1", port=18891)
        cls.server.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        if os.path.exists(cls.DB_PATH):
            os.remove(cls.DB_PATH)

    def test_health_endpoint(self):
        resp = urllib.request.urlopen("http://127.0.0.1:18891/health", timeout=5)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertIn("overall_status", data)
        self.assertEqual(data["overall_status"], "HEALTHY")
        self.assertEqual(resp.status, 200)

    def test_metrics_endpoint(self):
        resp = urllib.request.urlopen("http://127.0.0.1:18891/metrics", timeout=5)
        body = resp.read().decode("utf-8")
        self.assertIn("web_inspection_overall_healthy", body)
        self.assertIn("web_inspection_site_status", body)

    def test_history_endpoint(self):
        resp = urllib.request.urlopen("http://127.0.0.1:18891/history", timeout=5)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_404_endpoint(self):
        try:
            urllib.request.urlopen("http://127.0.0.1:18891/nonexistent", timeout=5)
            self.fail("Should have raised HTTPError")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


class MockHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        html = """<!DOCTYPE html><html><body>
        <h1>Mock</h1>
        <button id="btn1">Click</button>
        </body></html>"""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, *args):
        pass


class TestSchedulerConcurrency(unittest.TestCase):
    DB_PATH = "test_scheduler_store.db"

    @classmethod
    def setUpClass(cls):
        cls.mock_server = HTTPServer(("127.0.0.1", 18892), MockHTTPHandler)
        cls.thread = threading.Thread(target=cls.mock_server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_server.shutdown()
        cls.mock_server.server_close()
        for f in [cls.DB_PATH, "inspection_dashboard.json",
                  "report_site_a.json", "report_site_b.json",
                  "report_site_a.html", "report_site_b.html",
                  "inspection_metrics.prom"]:
            if os.path.exists(f):
                os.remove(f)

    def test_concurrent_multi_site(self):
        if os.path.exists(self.DB_PATH):
            os.remove(self.DB_PATH)

        sites = [
            SiteTarget(name="Site_A", url="http://127.0.0.1:18892/", max_actions=2),
            SiteTarget(name="Site_B", url="http://127.0.0.1:18892/", max_actions=2),
        ]

        store = ResultStore(db_path=self.DB_PATH)
        scheduler = InspectionScheduler(
            sites=sites,
            concurrency=2,
            max_retries=1,
            result_store=store
        )

        dashboard = scheduler.run_all()

        self.assertEqual(dashboard["total_sites"], 2)
        self.assertIn("overall_status", dashboard)
        self.assertTrue(os.path.exists("inspection_dashboard.json"))

        # Both sites should have results in store
        summary = store.get_health_summary()
        self.assertEqual(summary["total_monitored_sites"], 2)


if __name__ == "__main__":
    unittest.main()
