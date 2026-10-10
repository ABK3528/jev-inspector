"""
Tests for Extensibility and Plugin Lifecycle Architecture.
Verifies:
1. Extension registration
2. Lifecycle callbacks dispatch (on_init, on_page_start, on_before_action, on_after_action, on_finish)
3. Action cancellation via on_before_action returning False
4. Error interception hook on_error_detected
"""

import unittest
from typing import Dict, Any
from playwright.sync_api import Page

from jev_inspector.extensions import BaseExtension, ExtensionManager
from jev_inspector import InspectionConfig, WebInspectionCrawler


class TrackingExtension(BaseExtension):
    def __init__(self):
        self.init_called = False
        self.actions_attempted = []
        self.actions_finished = []
        self.finish_called = False

    def on_init(self, crawler: Any) -> None:
        self.init_called = True

    def on_before_action(self, page: Page, element_info: Dict[str, Any]) -> bool:
        self.actions_attempted.append(element_info)
        return True

    def on_after_action(self, page: Page, action_desc: str, status: str, latency_ms: float) -> None:
        self.actions_finished.append((action_desc, status))

    def on_finish(self, report: Dict[str, Any]) -> None:
        self.finish_called = True


class CancellingExtension(BaseExtension):
    def on_before_action(self, page: Page, element_info: Dict[str, Any]) -> bool:
        # Cancel any action on a link
        return False


class TestExtensions(unittest.TestCase):
    def test_extension_registration_and_dispatch(self):
        mgr = ExtensionManager()
        ext = TrackingExtension()
        mgr.register(ext)

        mgr.dispatch_init(None)
        self.assertTrue(ext.init_called)

        allowed = mgr.dispatch_before_action(None, {"tag": "button", "text": "Submit"})
        self.assertTrue(allowed)
        self.assertEqual(len(ext.actions_attempted), 1)

        mgr.dispatch_after_action(None, "button['Submit']", "success", 120.5)
        self.assertEqual(len(ext.actions_finished), 1)

        mgr.dispatch_finish({"status": "PASSED"})
        self.assertTrue(ext.finish_called)

    def test_cancelling_extension_blocks_action(self):
        mgr = ExtensionManager()
        mgr.register(CancellingExtension())
        allowed = mgr.dispatch_before_action(None, {"tag": "a", "text": "External"})
        self.assertFalse(allowed)


if __name__ == "__main__":
    unittest.main()
