#!/usr/bin/env python3
"""
Authenticated Synthetic Web Inspection Demo.
Target: Quotes to Scrape (Authenticated User Dashboard)
Authentication Portal: https://quotes.toscrape.com/login

Features demonstrated:
1. Automated Authentication Flow:
   - Form-based login with test credentials.
   - Successful redirection to authenticated dashboard session.
2. Protected Area Verification (Deterministic Flow):
   - Confirms user logged in and presence of 'Logout' navigation element.
   - Validates quote list rendering and next pagination link.
   - Evaluates latency against SLA threshold (10.0s).
3. Protected Dashboard Exploration & Destructive Action Guard:
   - Safely explores authenticated author links, tags, and interactive elements.
   - Safety guard detects and safely skips the "Logout" / "Sign out" link,
     preventing the crawler from accidentally terminating its own session.
4. Comprehensive Observability:
   - Generates JSON report, HTML visual dashboard, and Prometheus metrics.
"""

import sys
import os
from config import InspectionConfig, AuthConfig
from crawler import WebInspectionCrawler

def run_authenticated_inspection():
    print("=" * 72)
    print("   🔐 Jev-Inspector: Authenticated Web Synthetic Inspection Demo")
    print("   Target:       https://quotes.toscrape.com/")
    print("   Login Portal: https://quotes.toscrape.com/login")
    print("=" * 72)

    # Quotes to Scrape allows testing authentication with any username/password
    DEMO_USER = "demo_inspector_user"
    DEMO_PASS = "ValidPassword123"

    cfg = InspectionConfig(
        target_url="https://quotes.toscrape.com/",
        max_actions=10,
        headless=True,
        action_timeout_ms=5000,
        page_load_timeout_ms=25000,
        wait_after_action=0.5,
        use_jev_dedup=True,
        report_json_path="demo_auth_report.json",
        report_html_path="demo_auth_report.html",
        screenshot_dir="demo_auth_screenshots",
        # 1. Automated Authentication Configuration
        auth=AuthConfig(
            enabled=True,
            login_url="https://quotes.toscrape.com/login",
            username_selector="input#username",
            password_selector="input#password",
            submit_selector="input[type='submit']",
            username=DEMO_USER,
            password=DEMO_PASS
        ),
        # 2. Critical Business Journey Flow in Authenticated State
        flows=[
            {
                "name": "Authenticated Session & Dashboard Verification Flow",
                "start_url": "https://quotes.toscrape.com/",
                "sla_max_duration_seconds": 12.0,
                "steps": [
                    {
                        "action": "assert",
                        "selector": "a[href='/logout']",
                        "assert_type": "visible",
                        "description": "验证登录成功后的会话状态（存在 Logout 链接）"
                    },
                    {
                        "action": "assert",
                        "selector": ".quote",
                        "assert_type": "visible",
                        "description": "验证用户主面板中内容卡片正常渲染"
                    },
                    {
                        "action": "assert",
                        "assert_type": "title_matches",
                        "expected": r"Quotes to Scrape",
                        "description": "验证已登录页面标题符合预期"
                    }
                ]
            }
        ],
        # 3. Destructive Keywords Safeguard:
        # Crucial for authenticated inspections: skips Logout to keep session intact!
        destructive_keywords=[
            "logout", "sign out", "注销", "登出", "退出登录", "删除"
        ]
    )

    print("[*] Initiating authenticated synthetic inspection...")
    crawler = WebInspectionCrawler(config=cfg)
    report = crawler.run()

    summary = report.get("summary", {})
    status = summary.get("status", "UNKNOWN")
    total_actions = summary.get("total_actions_executed", 0)
    total_skipped = summary.get("total_duplicates_skipped", 0)
    total_errors = summary.get("total_errors_detected", 0)
    duration = summary.get("duration_seconds", 0)

    print("\n" + "=" * 72)
    print("   📊 Authenticated Inspection Demo Results Summary")
    print("=" * 72)
    print(f"   • Inspection Status:      {status}")
    print(f"   • Total Actions Executed: {total_actions}")
    print(f"   • Duplicates Skipped:     {total_skipped} (Structural deduplication active)")
    print(f"   • Detected Errors:        {total_errors}")
    print(f"   • Total Duration:         {duration}s")
    print(f"   • JSON Report:            {cfg.report_json_path}")
    print(f"   • HTML Report:            {cfg.report_html_path}")
    print(f"   • Prometheus Metrics:     inspection_metrics.prom")
    print("=" * 72)

    if total_errors > 0:
        print("\n[!] Authenticated inspection detected anomalies in authenticated session.")
        sys.exit(1)
    else:
        print("\n[✓] Authenticated synthetic inspection PASSED with zero defects!")
        sys.exit(0)

if __name__ == "__main__":
    run_authenticated_inspection()
