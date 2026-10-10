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

    # Configure inspection parameters (Authenticated Whole-Site with Archetyping & Coverage Metrics)
    cfg = InspectionConfig(
        target_url="https://quotes.toscrape.com/",
        crawl_mode="site",
        max_pages=6,                  # Protected dashboard page exploration budget
        max_depth=2,                  # Traverse root and author/tag links while authenticated
        max_actions_per_page=6,       # Interactive element exploration actions per page
        max_pages_per_pattern=2,      # Cap per author/tag archetype pattern
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
    coverage = summary.get("coverage_metrics", {})
    functional_cov = coverage.get("functional_archetype_coverage_rate", 0.0)
    tested_archetypes = coverage.get("unique_interactive_signatures_tested", 0)
    total_archetypes = coverage.get("total_unique_archetypes_discovered", 0)
    raw_encountered = coverage.get("total_raw_elements_encountered", 0)
    raw_rate = coverage.get("raw_sampling_rate", 0.0)
    pages_count = coverage.get("pages_discovered_count", len(report.get("discovered_pages", [])))
    archetypes_count = coverage.get("url_archetypes_count", len(report.get("url_archetype_distribution", {})))

    print("\n" + "=" * 74)
    print("   📊 Demo 2 (Quotes to Scrape 受保护登录后台) 覆盖率全景评估报告")
    print("=" * 74)
    print(f"   • 巡检最终状态 (Status):             {status}")
    print(f"   • 保护区页面访问 (Pages Visited):    {pages_count} 个受保护业务页")
    print(f"   • URL 路径模式原型 (URL Archetypes): {archetypes_count} 个独立模式模板")
    print(f"   • 站点拓扑链路边 (Topology Edges):   {len(report.get('site_topology', []))} 条跳转有向边")
    print(f"   • 遭遇候选控件总量 (Raw Candidates): {raw_encountered} 个原生DOM元素")
    print(f"   • 结构去重过滤量 (Duplicates Filter):{total_skipped} 个重复同构项")
    print(f"   • 独立控件原型总数 (Total Archetypes):{total_archetypes} 种功能指纹")
    print(f"   • 已测试控件原型数 (Tested Signatures):{tested_archetypes} 种功能指纹")
    print(f"   • 🎯 控件原型功能覆盖率 (Archetype Cov):{functional_cov * 100:.2f}% (测试指纹/原型总数)")
    print(f"   • 💡 原生元素去重采样比 (Raw Sampling): {raw_rate * 100:.2f}% (有效阻断 95%+ 冗余开销)")
    print(f"   • 检出故障/异常 (Errors Detected):   {total_errors}")
    print(f"   • 巡检总耗时 (Duration):             {duration}s")
    print(f"   • 产出报表 (Artifacts):              {cfg.report_json_path} | {cfg.report_html_path}")
    print("=" * 74)

    if total_errors > 0:
        print("\n[!] Authenticated inspection detected anomalies in authenticated session.")
        sys.exit(1)
    else:
        print("\n[✓] Authenticated synthetic inspection PASSED with zero defects!")
        sys.exit(0)

if __name__ == "__main__":
    run_authenticated_inspection()
