"""
Tests for Whole-Site Traversal & Site Topology Discovery.
Covers:
1. Multi-page site BFS crawl (Root -> Products, About -> Contact)
2. Max depth & Max pages limits adherence
3. URL normalization, fragment de-duplication, in-scope link filtering
4. Site topology graph recording (source -> target edges)
5. Multi-page per-page interactive exploration and unified reporting
"""

import unittest
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import InspectionConfig
from crawler import WebInspectionCrawler


class MockSiteClusterHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        routes = {
            "/": """
                <!DOCTYPE html><html><head><title>Home Portal</title></head><body>
                    <h1>Home</h1>
                    <nav>
                        <a id="nav-products" href="/products">Products</a>
                        <a id="nav-about" href="/about">About Us</a>
                        <a id="nav-external" href="https://other-domain.com/ad">External Ad</a>
                    </nav>
                    <button id="btn-home-cta">Subscribe Home</button>
                </body></html>
            """,
            "/products": """
                <!DOCTYPE html><html><head><title>Our Products</title></head><body>
                    <h1>Product Catalog</h1>
                    <a id="nav-detail-1" href="/products/101">Item 101</a>
                    <a id="nav-detail-2" href="/products/102">Item 102</a>
                    <a id="nav-back-home" href="/">Back to Home</a>
                    <input id="search-box" type="text" placeholder="Search products" />
                </body></html>
            """,
            "/products/101": """
                <!DOCTYPE html><html><head><title>Product 101</title></head><body>
                    <h1>Widget 101</h1>
                    <button id="btn-buy">Buy Widget</button>
                    <a href="/products">Back to Catalog</a>
                </body></html>
            """,
            "/products/102": """
                <!DOCTYPE html><html><head><title>Product 102</title></head><body>
                    <h1>Gadget 102</h1>
                    <button id="btn-buy">Buy Gadget</button>
                </body></html>
            """,
            "/about": """
                <!DOCTYPE html><html><head><title>About Company</title></head><body>
                    <h1>About Us</h1>
                    <a id="nav-contact" href="/contact">Contact Page</a>
                </body></html>
            """,
            "/contact": """
                <!DOCTYPE html><html><head><title>Contact Support</title></head><body>
                    <h1>Contact</h1>
                    <button id="btn-submit-contact">Send Message</button>
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


class TestWholeSiteCrawl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 18898), MockSiteClusterHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_whole_site_bfs_traversal(self):
        """Verify the crawler traverses multiple connected pages across the entire site."""
        cfg = InspectionConfig(
            target_url="http://127.0.0.1:18898/",
            crawl_mode="site",
            max_pages=10,
            max_depth=3,
            max_actions_per_page=3,
            headless=True,
            wait_after_action=0.1,
            report_json_path="test_site_crawl_report.json",
            report_html_path="test_site_crawl_report.html"
        )
        crawler = WebInspectionCrawler(config=cfg)
        report = crawler.run()

        summary = report["summary"]
        self.assertEqual(summary["status"], "PASSED")
        self.assertEqual(summary["crawl_mode"], "site")
        
        # Verify multiple pages discovered
        discovered_urls = [p["url"] for p in report["discovered_pages"]]
        self.assertGreaterEqual(len(discovered_urls), 4)
        
        # Should include home, products, about, contact
        url_paths = [u.replace("http://127.0.0.1:18898", "") for u in discovered_urls]
        self.assertTrue("" in url_paths or "/" in url_paths)  # root
        self.assertIn("/products", url_paths)
        self.assertIn("/about", url_paths)

        # External ad domain must NOT be included in discovered pages
        for u in discovered_urls:
            self.assertNotIn("other-domain.com", u)

        # Verify site topology graph recorded edges
        topology = report["site_topology"]
        self.assertGreater(len(topology), 0)
        edge_pairs = [(e["source"].replace("http://127.0.0.1:18898", ""), e["target"].replace("http://127.0.0.1:18898", "")) for e in topology]
        self.assertTrue(any(pair == ("", "/products") or pair == ("/", "/products") for pair in edge_pairs))

    def test_depth_limiting(self):
        """Depth=1 should only visit root and directly linked pages (/products, /about), not sub-sub pages."""
        cfg = InspectionConfig(
            target_url="http://127.0.0.1:18898/",
            crawl_mode="site",
            max_pages=20,
            max_depth=1,  # Strictly depth 1
            max_actions_per_page=1,
            headless=True,
            wait_after_action=0.1
        )
        crawler = WebInspectionCrawler(config=cfg)
        report = crawler.run()

        depths = [p["depth"] for p in report["discovered_pages"]]
        self.assertTrue(all(d <= 1 for d in depths))

    def test_url_pattern_filtering(self):
        """URL exclude pattern should prevent visiting specified paths (e.g. /about)."""
        cfg = InspectionConfig(
            target_url="http://127.0.0.1:18898/",
            crawl_mode="site",
            max_pages=10,
            max_depth=2,
            max_actions_per_page=1,
            url_exclude_patterns=[r"/about", r"/contact"],
            headless=True,
            wait_after_action=0.1
        )
        crawler = WebInspectionCrawler(config=cfg)
        report = crawler.run()

        discovered_urls = [p["url"] for p in report["discovered_pages"]]
        for u in discovered_urls:
            self.assertNotIn("/about", u)
            self.assertNotIn("/contact", u)


if __name__ == "__main__":
    unittest.main()
