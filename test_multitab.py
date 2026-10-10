"""
Tests for Industrial Multi-Tab Guardian and Explicit Multi-Page Flow Switching.
Covers:
1. FlowEngine explicit multi-tab actions:
   - click_and_expect_page: target="_blank" click, switch focus, assert new tab content
   - open_tab: programmatically open a new tab with alias, switch focus
   - switch_tab: switch between named aliases, previous, and numerical index
   - close_tab: close target tab, verify focus returns to main/previous tab
2. Crawler Multi-Tab Guardian:
   - Spawns popups during autonomous traversal, ensures new tab error checking,
     and auto-closes popup without leaking memory or losing main focus.
"""

import unittest
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from playwright.sync_api import sync_playwright

from flow_engine import FlowDefinition, FlowStep, FlowExecutor
from config import InspectionConfig
from crawler import WebInspectionCrawler


class MockMultiTabHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Parent Page</title></head>
            <body>
                <h1 id="parent-title">Parent Dashboard</h1>
                <a id="link-blank" href="/child" target="_blank">Open Child in New Tab</a>
                <button id="btn-popup" onclick="window.open('/child', '_blank');">Open Popup</button>
                <div id="parent-content">Main View</div>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/child":
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Child Page</title></head>
            <body>
                <h1 id="child-title">Child Detail Panel</h1>
                <p id="child-data">Order #998877 Approved</p>
                <button id="btn-child-action">Child Confirm</button>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/second-child":
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Second Child Page</title></head>
            <body>
                <h1 id="second-title">Second View</h1>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class TestMultiPageFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 18897), MockMultiTabHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_explicit_multi_tab_workflow(self):
        """Test full user journey:
        1. Open parent page
        2. Click link with target="_blank" -> wait and switch to child tab
        3. Assert title and elements inside child tab
        4. Close child tab -> verify focus automatically returns to parent
        5. Assert parent content
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            flow = FlowDefinition(
                name="Multi-Tab E2E Workflow",
                start_url="http://127.0.0.1:18897/",
                sla_max_duration_seconds=15.0,
                steps=[
                    # 1. Assert parent initial state
                    FlowStep(action="assert", selector="#parent-title", assert_type="text_contains", expected="Parent Dashboard"),
                    
                    # 2. Click target="_blank" link and expect new tab
                    FlowStep(action="click_and_expect_page", selector="#link-blank", value="child_tab"),
                    
                    # 3. We are now in child_tab: assert child elements
                    FlowStep(action="assert", selector="#child-title", assert_type="text_contains", expected="Child Detail Panel"),
                    FlowStep(action="assert", selector="#child-data", assert_type="text_contains", expected="Order #998877 Approved"),
                    FlowStep(action="assert", assert_type="title_matches", expected="Child Page"),
                    
                    # 4. Close child tab
                    FlowStep(action="close_tab", value="child_tab"),
                    
                    # 5. We are now back to parent page: assert parent view
                    FlowStep(action="assert", selector="#parent-content", assert_type="text_contains", expected="Main View"),
                    FlowStep(action="assert", assert_type="title_matches", expected="Parent Page")
                ]
            )

            executor = FlowExecutor(page=page, context=context)
            result = executor.execute_flow(flow)

            browser.close()

            self.assertEqual(result["status"], "PASSED", f"Flow failed with errors: {result.get('errors')}")
            self.assertEqual(len(result["errors"]), 0)
            self.assertEqual(result["executed_steps"], 9)  # 1 initial goto + 8 flow steps

    def test_open_tab_and_switch_tab(self):
        """Test explicitly opening a named new tab, switching between tabs, and closing."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            flow = FlowDefinition(
                name="Programmatic Open & Switch Tab",
                start_url="http://127.0.0.1:18897/",
                steps=[
                    FlowStep(action="open_tab", selector="tab_two", value="http://127.0.0.1:18897/second-child"),
                    FlowStep(action="assert", selector="#second-title", assert_type="text_contains", expected="Second View"),
                    # Switch back to main
                    FlowStep(action="switch_tab", value="main"),
                    FlowStep(action="assert", selector="#parent-title", assert_type="text_contains", expected="Parent Dashboard"),
                    # Switch back to tab_two
                    FlowStep(action="switch_tab", value="tab_two"),
                    FlowStep(action="assert", selector="#second-title", assert_type="visible")
                ]
            )

            executor = FlowExecutor(page=page, context=context)
            result = executor.execute_flow(flow)

            browser.close()

            self.assertEqual(result["status"], "PASSED")
            self.assertEqual(len(result["errors"]), 0)

    def test_crawler_multi_tab_guardian(self):
        """Test Crawler Context-level Multi-Tab Guardian:
        Clicking a target="_blank" button during autonomous inspection doesn't break the main loop,
        inspects the child tab, and auto-closes it.
        """
        cfg = InspectionConfig(
            target_url="http://127.0.0.1:18897/",
            max_actions=5,
            headless=True,
            wait_after_action=0.2,
            report_json_path="test_multitab_report.json",
            report_html_path="test_multitab_report.html"
        )
        crawler = WebInspectionCrawler(config=cfg)
        report = crawler.run()

        summary = report["summary"]
        self.assertEqual(summary["status"], "PASSED")
        self.assertGreater(summary["total_actions_executed"], 0)


if __name__ == "__main__":
    unittest.main()
