"""
Unit and Integration Tests for Web Inspection Engine.
Covers:
1. Configuration loading and env overrides
2. AlertManager payload formatters for all channels (Feishu, DingTalk, WeCom, Slack, Generic)
3. Structural signature generation & deduplication logic
4. Destructive keyword safety guards
5. Prometheus metrics serialization
6. End-to-end synthetic crawl with local mock server
"""

import os
import json
import unittest
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from config import InspectionConfig, AuthConfig, AlertConfig
from alert_manager import AlertManager
from crawler import WebInspectionCrawler
from jev_client import JevClient

class MockJevClient:
    """Mock Jev model for deterministic offline testing."""
    def __init__(self, should_detect_error=False):
        self.should_detect_error = should_detect_error
        self.model = "mock-jev"
        self.base_url = "http://mock-jev.local"

    def judge_error(self, page_feedback: str):
        if "500" in page_feedback or "crash" in page_feedback.lower() or "error" in page_feedback.lower():
            return {
                "is_error": True,
                "error_type": "system_error",
                "confidence": 0.95,
                "severity_score": 0.85
            }
        return {
            "is_error": False,
            "error_type": "normal_info",
            "confidence": 0.9,
            "severity_score": 0.0
        }

    def should_skip_duplicate(self, element_summary: str, seen_signatures: list):
        return "duplicate_item" in element_summary

class TestInspectionConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = InspectionConfig()
        self.assertEqual(cfg.max_actions, 30)
        self.assertTrue(cfg.headless)
        self.assertIn("注销", cfg.destructive_keywords)

    def test_from_file_and_env(self):
        test_file = "test_temp_config.json"
        with open(test_file, "w") as f:
            json.dump({"target_url": "https://example.com", "max_actions": 15}, f)
        
        try:
            cfg = InspectionConfig.from_file(test_file)
            self.assertEqual(cfg.target_url, "https://example.com")
            self.assertEqual(cfg.max_actions, 15)

            # Test env override
            os.environ["INSPECTION_TARGET_URL"] = "https://override.com"
            cfg.apply_env_overrides()
            self.assertEqual(cfg.target_url, "https://override.com")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
            os.environ.pop("INSPECTION_TARGET_URL", None)

class TestAlertManager(unittest.TestCase):
    def setUp(self):
        self.summary = {
            "target_url": "https://service.corp.internal/dashboard",
            "total_actions_executed": 12,
            "total_errors_detected": 1
        }
        self.errors = [{
            "action": "button['提交']",
            "detected_texts": ["HTTP 500 Internal Server Error"],
            "error_type": "system_error",
            "severity_score": 0.9
        }]

    def test_feishu_card_format(self):
        mgr = AlertManager(webhook_url=None, webhook_type="feishu")
        payload = mgr.format_payload("系统故障", self.summary, self.errors)
        self.assertEqual(payload["msg_type"], "interactive")
        self.assertIn("巡检告警", payload["card"]["header"]["title"]["content"])

    def test_dingtalk_format(self):
        mgr = AlertManager(webhook_url=None, webhook_type="dingtalk")
        payload = mgr.format_payload("系统故障", self.summary, self.errors)
        self.assertEqual(payload["msgtype"], "markdown")
        self.assertIn("https://service.corp.internal", payload["markdown"]["text"])

    def test_slack_format(self):
        mgr = AlertManager(webhook_url=None, webhook_type="slack")
        payload = mgr.format_payload("系统故障", self.summary, self.errors)
        self.assertIn("blocks", payload)
        self.assertEqual(len(payload["blocks"]), 2)

    def test_wecom_format(self):
        mgr = AlertManager(webhook_url=None, webhook_type="wecom")
        payload = mgr.format_payload("系统故障", self.summary, self.errors)
        self.assertEqual(payload["msgtype"], "text")
        self.assertIn("线上巡检告警", payload["text"]["content"])

class TestDestructiveGuardsAndSignatures(unittest.TestCase):
    def test_destructive_regex(self):
        cfg = InspectionConfig()
        crawler = WebInspectionCrawler(config=cfg, jev_client=MockJevClient())
        self.assertTrue(crawler.destructive_pattern.search("注销用户"))
        self.assertTrue(crawler.destructive_pattern.search("Sign Out"))
        self.assertTrue(crawler.destructive_pattern.search("format disk"))
        self.assertFalse(crawler.destructive_pattern.search("查询详情"))
        self.assertFalse(crawler.destructive_pattern.search("下一页"))

    def test_signature_generation(self):
        crawler = WebInspectionCrawler(config=InspectionConfig(), jev_client=MockJevClient())
        el1 = {
            "tag": "button",
            "role": "button",
            "text": "Item 1",
            "containerType": "tr",
            "pattern": "table > tbody > tr > td > button"
        }
        el2 = {
            "tag": "button",
            "role": "button",
            "text": "Item 2",
            "containerType": "tr",
            "pattern": "table > tbody > tr > td > button"
        }
        sig1 = crawler._generate_signature(el1)
        sig2 = crawler._generate_signature(el2)
        # Should match identical repeated container signature
        self.assertEqual(sig1, sig2)

class MockHTTPHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Mock Inspection Target</title></head>
            <body>
                <h1>Mock App</h1>
                <button id="btn-normal" onclick="document.getElementById('msg').innerText = 'OK';">正常按钮</button>
                <button id="btn-err" onclick="document.getElementById('msg').innerText = '500 Internal Server Error';">错误触发</button>
                <button id="btn-logout">退出登录</button>
                <div id="msg"></div>
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

class TestEndToEndMockCrawler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start local mock HTTP server
        cls.server = HTTPServer(("127.0.0.1", 18899), MockHTTPHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_mock_inspection_flow(self):
        cfg = InspectionConfig(
            target_url="http://127.0.0.1:18899/",
            max_actions=5,
            headless=True,
            wait_after_action=0.2,
            report_json_path="test_mock_report.json",
            report_html_path="test_mock_report.html"
        )
        mock_jev = MockJevClient()
        crawler = WebInspectionCrawler(config=cfg, jev_client=mock_jev)
        report = crawler.run()

        # Check summary
        summary = report["summary"]
        self.assertGreater(summary["total_actions_executed"], 0)
        self.assertTrue(os.path.exists("test_mock_report.json"))
        self.assertTrue(os.path.exists("inspection_metrics.prom"))

        # Destructive action ("退出登录") should be skipped and never executed
        executed_texts = [a["action"] for a in report["executed_actions"]]
        for act in executed_texts:
            self.assertNotIn("退出登录", act)

        # Cleanup
        if os.path.exists("test_mock_report.json"):
            os.remove("test_mock_report.json")
        if os.path.exists("test_mock_report.html"):
            os.remove("test_mock_report.html")

if __name__ == "__main__":
    unittest.main()
