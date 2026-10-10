# Backward-compatible proxy module forwarding to jev_inspector.core.config
from jev_inspector.core.config import InspectionConfig, AuthConfig, AlertConfig

__all__ = ["InspectionConfig", "AuthConfig", "AlertConfig"]
