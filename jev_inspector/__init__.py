"""
Jev-Inspector: Enterprise-grade Autonomous Web Synthetic Monitoring & Error Hunting Platform.
"""

from .core.config import InspectionConfig, AuthConfig, AlertConfig
from .engine.crawler import WebInspectionCrawler, WebCrawler
from .engine.flow_engine import FlowDefinition, FlowStep, FlowExecutor
from .decision.jev_client import JevClient
from .alert.alert_manager import AlertManager
from .scheduler.scheduler import SiteTarget, ResultStore, InspectionScheduler, HealthCheckServer
from .extensions.base import BaseExtension, ExtensionManager

__version__ = "1.0.0"

__all__ = [
    # Core Config
    "InspectionConfig",
    "AuthConfig",
    "AlertConfig",
    # Engine
    "WebInspectionCrawler",
    "WebCrawler",
    "FlowDefinition",
    "FlowStep",
    "FlowExecutor",
    # Decision
    "JevClient",
    # Alert
    "AlertManager",
    # Scheduler
    "SiteTarget",
    "ResultStore",
    "InspectionScheduler",
    "HealthCheckServer",
    # Extensibility
    "BaseExtension",
    "ExtensionManager",
]
