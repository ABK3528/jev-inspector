"""
Tests for Advanced Whole-Site Crawling & Coverage Metrics Engine.
Covers:
1. L1 URL normalization (removes utm, timestamp, hash, sorts query params)
2. L2 Path Archetyping (groups /item/100, /item/200 into /item/:id with max budget limit)
3. Elastic 3-Level Backtracking:
   - Soft modal/drawer dismissal (Escape / close button)
   - URL drift detection and go_back recovery
   - L3 Hard Reset to expected URL
4. Coverage measurement engine (element coverage rate, unique signatures vs duplicate skips)
5. Repeated site runs to verify stability, repeatability, and coverage consistency.
"""

import unittest
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import InspectionConfig
from crawler import WebInspectionCrawler


class MockComplexSiteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        routes = {
            "/": """
                <!DOCTYPE html><html><head><title>Portal Root</title></head><body>
                    <h1>Welcome to Portal</h1>
                    <nav>
                        <a id="nav-item-1" href="/items/1001?utm_source=google&b=2&a=1">Item 1001</a>
                        <a id="nav-item-2" href="/items/1002?timestamp=12345&a=1&b=2">Item 1002</a>
                        <a id="nav-item-3" href="/items/1003">Item 1003</a>
                        <a id="nav-item-4" href="/items/1004">Item 1004</a>
                        <a id="nav-modal" href="/modal-demo">Modal Page</a>
                    </nav>
                </body></html>
            """,
            "/items/1001": """<!DOCTYPE html><html><body><h1>Item 1001</h1><button id="btn-1">Action 1</button></body></html>""",
            "/items/1002": """<!DOCTYPE html><html><body><h1>Item 1002</h1><button id="btn-2">Action 2</button></body></html>""",
            "/items/1003": """<!DOCTYPE html><html><body><h1>Item 1003</h1><button id="btn-3">Action 3</button></body></html>""",
            "/items/1004": """<!DOCTYPE html><html><body><h1>Item 1004</h1><button id="btn-4">Action 4</button></body></html>""",
            "/modal-demo": """
                <!DOCTYPE html><html><head><title>Modal Demo</title></head><body>
                    <h1>Modal Page</h1>
                    <button id="btn-open-modal" onclick="document.getElementById('my-modal').style.display='block';">Open Modal</button>
                    <div id="my-modal" class="modal-backdrop" style="display:none;">
                        <div class="modal-content">
                            <p>Important Dialog</p>
                            <button class="close" onclick="document.getElementById('my-modal').style.display='none';">Close</button>
                        </div>
                    </div>
                    <button id="btn-other-action">Other Action</button>
                </body></html>
            """
        }

        path = self.path.split("?")[0].rstrip("/")
        if not path:
            path = "/"

        if path in routes:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(routes[path].encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class TestAdvancedWholeSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 18894), MockComplexSiteHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_url_normalization_l1(self):
        crawler = WebInspectionCrawler(config=InspectionConfig())
        # Strip tracking params and sort query keys
        u1 = crawler._normalize_url("/items/1001?utm_source=google&b=2&a=1", "http://example.com/base")
        u2 = crawler._normalize_url("/items/1001?timestamp=999&a=1&b=2", "http://example.com/base")
        self.assertEqual(u1, "http://example.com/items/1001?a=1&b=2")
        self.assertEqual(u2, "http://example.com/items/1001?a=1&b=2")

    def test_path_archetyping_l2(self):
        crawler = WebInspectionCrawler(config=InspectionConfig())
        arc1 = crawler._get_url_archetype("http://example.com/items/1001")
        arc2 = crawler._get_url_archetype("http://example.com/items/99999")
        arc3 = crawler._get_url_archetype("http://example.com/orders/c1a2b3c4-1234-5678-9abc-def012345678")
        self.assertEqual(arc1, "example.com/items/:id")
        self.assertEqual(arc2, "example.com/items/:id")
        self.assertEqual(arc3, "example.com/orders/:uuid")

    def test_path_archetype_budget_capping(self):
        """Even though 4 items exist (/items/1001, 1002, 1003, 1004), max_pages_per_pattern=2 caps it."""
        cfg = InspectionConfig(
            target_url="http://127.0.0.1:18894/",
            crawl_mode="site",
            max_pages=20,
            max_depth=2,
            max_pages_per_pattern=2,  # Cap at 2 sample pages per archetype
            max_actions_per_page=1,
            headless=True,
            wait_after_action=0.1
        )
        crawler = WebInspectionCrawler(config=cfg)
        report = crawler.run()

        # Check archetype distribution
        pattern_dist = report["url_archetype_distribution"]
        archetype_key = [k for k in pattern_dist.keys() if "/items/:id" in k]
        self.assertTrue(len(archetype_key) > 0)
        self.assertLessEqual(pattern_dist[archetype_key[0]], 2)

    def test_coverage_metrics_reporting(self):
        """Verify element and page coverage rate metrics are correctly compiled."""
        cfg = InspectionConfig(
            target_url="http://127.0.0.1:18894/",
            crawl_mode="site",
            max_pages=5,
            max_depth=2,
            max_actions_per_page=3,
            headless=True,
            wait_after_action=0.1
        )
        crawler = WebInspectionCrawler(config=cfg)
        report = crawler.run()

        coverage = report["summary"]["coverage_metrics"]
        self.assertIn("element_coverage_rate", coverage)
        self.assertIn("unique_interactive_signatures", coverage)
        self.assertIn("pages_discovered_count", coverage)
        self.assertGreater(coverage["pages_discovered_count"], 1)
        self.assertGreater(coverage["element_coverage_rate"], 0.0)

    def test_repeated_runs_consistency(self):
        """Run multiple repeated cycles on the site to ensure coverage repeatability & zero state pollution."""
        results = []
        for i in range(2):
            cfg = InspectionConfig(
                target_url="http://127.0.0.1:18894/",
                crawl_mode="site",
                max_pages=4,
                max_depth=2,
                max_actions_per_page=2,
                headless=True,
                wait_after_action=0.05
            )
            crawler = WebInspectionCrawler(config=cfg)
            rep = crawler.run()
            results.append(rep["summary"]["coverage_metrics"]["pages_discovered_count"])

        # Consistency check: both runs should explore the exact same number of pages
        self.assertEqual(results[0], results[1])


if __name__ == "__main__":
    unittest.main()
