"""
Configuration manager for Online Web Inspection Tool.
Supports YAML/JSON configuration files with schema validation,
environment variable overrides, and production defaults.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class AuthConfig:
    enabled: bool = False
    login_url: Optional[str] = None
    username_selector: Optional[str] = None
    password_selector: Optional[str] = None
    submit_selector: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    storage_state_path: Optional[str] = None

@dataclass
class AlertConfig:
    enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_type: str = "generic" # generic, feishu, dingtalk, wecom, slack
    alert_on_warning: bool = False
    min_severity_score: float = 0.5

@dataclass
class InspectionConfig:
    # Target
    target_url: str = "https://the-internet.herokuapp.com/status_codes"
    allowed_domains: List[str] = field(default_factory=list)
    
    # Traversal parameters
    max_actions: int = 30
    action_timeout_ms: int = 5000
    page_load_timeout_ms: int = 25000
    wait_after_action: float = 1.0
    headless: bool = True
    
    # User Journey Flow Definitions (optional deterministic flows)
    flows: List[Dict[str, Any]] = field(default_factory=list)
    
    # Destructive safeguards
    destructive_keywords: List[str] = field(default_factory=lambda: [
        "注销", "登出", "退出登录", "删除账号", "清空数据库", "清空全部",
        "drop table", "drop database", "format disk", "delete account",
        "sign out", "logout", "destroy", "purge"
    ])
    
    # Jev / Decision Engine
    api_key: Optional[str] = None
    base_url: str = "https://api.typesafe.ai/v1/systemone"
    model: str = "jev-latest"
    use_jev_dedup: bool = True
    
    # Auth & State
    auth: AuthConfig = field(default_factory=AuthConfig)
    
    # Reporting & Alerts
    report_json_path: str = "traversal_report.json"
    report_html_path: str = "traversal_report.html"
    screenshot_dir: str = "screenshots"
    alert: AlertConfig = field(default_factory=AlertConfig)

    # Resilience
    max_consecutive_failures: int = 5
    page_recovery_retries: int = 2

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InspectionConfig":
        auth_data = data.pop("auth", {})
        alert_data = data.pop("alert", {})
        
        auth_cfg = AuthConfig(**auth_data) if isinstance(auth_data, dict) else AuthConfig()
        alert_cfg = AlertConfig(**alert_data) if isinstance(alert_data, dict) else AlertConfig()
        
        # Filter matching keys
        valid_keys = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        
        return cls(auth=auth_cfg, alert=alert_cfg, **filtered_data)

    @classmethod
    def from_file(cls, filepath: str) -> "InspectionConfig":
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return cls.from_dict(data)

    def apply_env_overrides(self):
        """Allow environment variables to override sensitive configurations."""
        if os.getenv("INSPECTION_TARGET_URL"):
            self.target_url = os.getenv("INSPECTION_TARGET_URL")
        if os.getenv("TYPESAFE_API_KEY"):
            self.api_key = os.getenv("TYPESAFE_API_KEY")
        if os.getenv("INSPECTION_WEBHOOK_URL"):
            self.alert.webhook_url = os.getenv("INSPECTION_WEBHOOK_URL")
            self.alert.enabled = True
        if os.getenv("INSPECTION_MAX_ACTIONS"):
            self.max_actions = int(os.getenv("INSPECTION_MAX_ACTIONS"))
        if os.getenv("INSPECTION_HEADLESS"):
            self.headless = os.getenv("INSPECTION_HEADLESS").lower() in ("true", "1", "yes")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
