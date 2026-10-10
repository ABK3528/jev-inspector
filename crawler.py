# Backward-compatible proxy module forwarding to jev_inspector.engine.crawler
from jev_inspector.engine.crawler import WebInspectionCrawler, WebCrawler

__all__ = ["WebInspectionCrawler", "WebCrawler"]
