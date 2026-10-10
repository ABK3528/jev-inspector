"""
Tests for FlowEngine and assertion verification.
Covers:
1. FlowDefinition dataclass and dict parsing
2. End-to-end execution of flow steps (goto, click, fill, assert text_contains, assert visible, assert title)
3. Negative tests: assertion failures, timeout failures, SLA threshold breach
"""

import unittest
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from playwright.sync_api import sync_playwright

from flow_engine import FlowDefinition, FlowStep, FlowExecutor


class MockFlowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Portal Login</title></head>
            <body>
                <h1 id="title">Welcome</h1>
                <form action="/dashboard" method="GET">
                    <input id="username" name="username" type="text" placeholder="Username" />
                    <button id="login-btn" type="submit">Log In</button>
                </form>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        elif self.path.startswith("/dashboard"):
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>System Dashboard</title></head>
            <body>
                <div id="welcome-banner">Hello, admin! Welcome to the console.</div>
                <div id="metric-card" style="display: block;">System OK</div>
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


class TestFlowEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 18895), MockFlowHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_flow_parsing(self):
        data = {
            "name": "Login Flow",
            "start_url": "http://127.0.0.1:18895/",
            "sla_max_duration_seconds": 15.0,
            "steps": [
                {"action": "fill", "selector": "#username", "value": "admin"},
                {"action": "click", "selector": "#login-btn"},
                {"action": "assert", "selector": "#welcome-banner", "assert_type": "text_contains", "expected": "Hello, admin"}
            ]
        }
        flow = FlowDefinition.from_dict(data)
        self.assertEqual(flow.name, "Login Flow")
        self.assertEqual(len(flow.steps), 3)
        self.assertEqual(flow.steps[2].assert_type, "text_contains")

    def test_successful_flow_execution(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            flow = FlowDefinition(
                name="E2E Login & Verification",
                start_url="http://127.0.0.1:18895/",
                sla_max_duration_seconds=10.0,
                steps=[
                    FlowStep(action="assert", selector="#title", assert_type="text_contains", expected="Welcome"),
                    FlowStep(action="fill", selector="#username", value="admin"),
                    FlowStep(action="click", selector="#login-btn"),
                    FlowStep(action="assert", selector="#welcome-banner", assert_type="text_contains", expected="Hello, admin!"),
                    FlowStep(action="assert", selector="#metric-card", assert_type="visible"),
                    FlowStep(action="assert", assert_type="title_matches", expected="System Dashboard"),
                    FlowStep(action="assert", assert_type="url_matches", expected=r"/dashboard")
                ]
            )

            executor = FlowExecutor(page)
            result = executor.execute_flow(flow)

            browser.close()

            self.assertEqual(result["status"], "PASSED")
            self.assertEqual(len(result["errors"]), 0)
            self.assertFalse(result["sla_breached"])
            self.assertEqual(result["executed_steps"], 8)  # 1 goto + 7 steps

    def test_assertion_failure_handling(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            flow = FlowDefinition(
                name="Failing Assertion Flow",
                start_url="http://127.0.0.1:18895/",
                steps=[
                    FlowStep(action="assert", selector="#title", assert_type="text_contains", expected="NonExistentText", timeout_ms=1000)
                ]
            )

            executor = FlowExecutor(page)
            result = executor.execute_flow(flow)

            browser.close()

            self.assertEqual(result["status"], "FAILED")
            self.assertGreater(len(result["errors"]), 0)
            self.assertIn("NonExistentText", result["errors"][0]["error"])

    def test_sla_breach_detection(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            flow = FlowDefinition(
                name="SLA Breach Test",
                start_url="http://127.0.0.1:18895/",
                sla_max_duration_seconds=0.01,  # Impossibly short SLA
                steps=[
                    FlowStep(action="wait", value="0.1")
                ]
            )

            executor = FlowExecutor(page)
            result = executor.execute_flow(flow)

            browser.close()

            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(result["sla_breached"])
            self.assertTrue(any(e.get("action") == "sla_check" for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
