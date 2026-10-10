"""
Jev-Inspector Extensibility Hooks & Plugin Architecture.
Provides lifecycle extension points:
- on_page_discovered: Before/after a new page is enqueued
- on_before_action: Pre-action guard or payload mutator
- on_after_action: Post-action validation, metrics recorder
- on_error_detected: Custom error dispatcher, sentry forwarder, ticket creator
- custom_evaluator: Alternate AI/Rule evaluator hook
"""

from typing import Dict, Any, List, Optional, Callable
from playwright.sync_api import Page
import logging

logger = logging.getLogger("inspection.extension")

class BaseExtension:
    """Base class for all inspection lifecycle plugins."""

    def on_init(self, crawler: Any) -> None:
        """Called once when crawler initializes."""
        pass

    def on_page_start(self, page: Page, url: str) -> None:
        """Called when a page navigation starts."""
        pass

    def on_page_loaded(self, page: Page, url: str) -> None:
        """Called when page DOM is loaded and ready for element discovery."""
        pass

    def on_before_action(self, page: Page, element_info: Dict[str, Any]) -> bool:
        """
        Called before an interaction action executes.
        Return False to cancel/skip this action.
        """
        return True

    def on_after_action(self, page: Page, action_desc: str, status: str, latency_ms: float) -> None:
        """Called after an interaction action completes."""
        pass

    def on_error_detected(self, error_record: Dict[str, Any]) -> None:
        """Called immediately when an error (HTTP/Console/Toast) is detected."""
        pass

    def on_finish(self, report: Dict[str, Any]) -> None:
        """Called when the inspection run is completed, before saving the report."""
        pass


class ExtensionManager:
    """Manages registered extensions and dispatches lifecycle events."""

    def __init__(self):
        self._extensions: List[BaseExtension] = []

    def register(self, extension: BaseExtension) -> None:
        self._extensions.append(extension)
        logger.info(f"Registered extension: {extension.__class__.__name__}")

    def dispatch_init(self, crawler: Any) -> None:
        for ext in self._extensions:
            try:
                ext.on_init(crawler)
            except Exception as e:
                logger.error(f"Extension {ext.__class__.__name__}.on_init failed: {e}")

    def dispatch_page_start(self, page: Page, url: str) -> None:
        for ext in self._extensions:
            try:
                ext.on_page_start(page, url)
            except Exception as e:
                logger.error(f"Extension {ext.__class__.__name__}.on_page_start failed: {e}")

    def dispatch_page_loaded(self, page: Page, url: str) -> None:
        for ext in self._extensions:
            try:
                ext.on_page_loaded(page, url)
            except Exception as e:
                logger.error(f"Extension {ext.__class__.__name__}.on_page_loaded failed: {e}")

    def dispatch_before_action(self, page: Page, element_info: Dict[str, Any]) -> bool:
        for ext in self._extensions:
            try:
                if not ext.on_before_action(page, element_info):
                    return False
            except Exception as e:
                logger.error(f"Extension {ext.__class__.__name__}.on_before_action failed: {e}")
        return True

    def dispatch_after_action(self, page: Page, action_desc: str, status: str, latency_ms: float) -> None:
        for ext in self._extensions:
            try:
                ext.on_after_action(page, action_desc, status, latency_ms)
            except Exception as e:
                logger.error(f"Extension {ext.__class__.__name__}.on_after_action failed: {e}")

    def dispatch_error_detected(self, error_record: Dict[str, Any]) -> None:
        for ext in self._extensions:
            try:
                ext.on_error_detected(error_record)
            except Exception as e:
                logger.error(f"Extension {ext.__class__.__name__}.on_error_detected failed: {e}")

    def dispatch_finish(self, report: Dict[str, Any]) -> None:
        for ext in self._extensions:
            try:
                ext.on_finish(report)
            except Exception as e:
                logger.error(f"Extension {ext.__class__.__name__}.on_finish failed: {e}")
