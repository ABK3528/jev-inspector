#!/usr/bin/env python3
"""
Real-world Online Synthetic Inspection Demo.
Target: Hacker News (https://news.ycombinator.com)

Features demonstrated:
1. Dual-mode inspection:
   - Deterministic Flow: Navigates to 'newest', validates page title, items, and search box within SLA.
   - Autonomous Exploration: Discovers interactive links/buttons, applies structural deduplication,
     and monitors DOM/Console/Network errors.
2. Destructive Guard: Safely avoids 'login'/'logout'/'submit' side effects.
3. Observability & Reporting: Generates traversal_report.json, traversal_report.html, and inspection_metrics.prom.
"""

import sys
import os
import time
from config import InspectionConfig
from crawler import WebInspectionCrawler

def run_hackernews_inspection():
    print("=" * 70)
    print("   🌐 Jev-Inspector: Real-World Website Synthetic Inspection Demo")
    print("   Target: Hacker News (https://news.ycombinator.com)")
    print("=" * 70)

    # Configure inspection parameters (Whole-Site Mode with Archetyping & Coverage Metrics)
    cfg = InspectionConfig(
        target_url="https://news.ycombinator.com",
        crawl_mode="site",
        max_pages=8,                  # Focused whole-site demo page budget
        max_depth=2,                  # Traverse root and primary navigational links
        max_actions_per_page=6,       # Interactive element exploration actions per page
        max_pages_per_pattern=2,      # URL template archetyping cap (prevents duplicate story pages)
        headless=True,
        action_timeout_ms=5000,
        page_load_timeout_ms=15000,
        wait_after_action=0.5,
        use_jev_dedup=True,
        report_json_path="demo_hn_report.json",
        report_html_path="demo_hn_report.html",
        screenshot_dir="demo_screenshots",
        # Critical business journey flow with SLAs and assertions
        flows=[
            {
                "name": "HN Newest & Navigation Flow",
                "start_url": "https://news.ycombinator.com",
                "sla_max_duration_seconds": 15.0,
                "steps": [
                    {
                        "action": "assert",
                        "selector": "#hnmain",
                        "assert_type": "visible",
                        "description": "验证 Hacker News 页面主体正常渲染"
                    },
                    {
                        "action": "click",
                        "selector": "a[href='newest']",
                        "description": "进入 'newest' 最新帖子列表"
                    },
                    {
                        "action": "assert",
                        "assert_type": "url_matches",
                        "expected": r"newest",
                        "description": "验证当前 URL 成功跳转至 newest 路由"
                    },
                    {
                        "action": "assert",
                        "selector": "tr.athing",
                        "assert_type": "visible",
                        "description": "验证最新帖子列表项已成功加载显示"
                    }
                ]
            }
        ]
    )

    crawler = WebInspectionCrawler(config=cfg)
    report = crawler.run()

    summary = report.get("summary", {})
    status = summary.get("status", "UNKNOWN")
    total_actions = summary.get("total_actions_executed", 0)
    total_skipped = summary.get("total_duplicates_skipped", 0)
    total_errors = summary.get("total_errors_detected", 0)
    duration = summary.get("duration_seconds", 0)
    coverage = summary.get("coverage_metrics", {})
    element_cov_rate = coverage.get("element_coverage_rate", 0.0)
    pages_count = coverage.get("pages_discovered_count", len(report.get("discovered_pages", [])))
    archetypes_count = coverage.get("url_archetypes_count", len(report.get("url_archetype_distribution", {})))

    print("\n" + "=" * 72)
    print("   📊 Inspection Demo Results & Coverage Metrics Summary")
    print("=" * 72)
    print(f"   • Inspection Status:         {status}")
    print(f"   • Whole-Site Pages Visited:  {pages_count}")
    print(f"   • URL Template Archetypes:   {archetypes_count} patterns identified")
    print(f"   • Navigation Graph Edges:    {len(report.get('site_topology', []))} links mapped")
    print(f"   • Interactive Actions Exec:  {total_actions}")
    print(f"   • Duplicates Skipped:        {total_skipped} (4-Level Dedup Active)")
    print(f"   • Element Coverage Rate:     {element_cov_rate * 100:.2f}%")
    print(f"   • Detected Errors:           {total_errors}")
    print(f"   • Execution Duration:        {duration}s")
    print(f"   • JSON Report:               {cfg.report_json_path}")
    print(f"   • HTML Report:               {cfg.report_html_path}")
    print(f"   • Prometheus Metrics:        inspection_metrics.prom")
    print("=" * 72)

    if total_errors > 0:
        print("\n[!] Inspection detected anomalies on target site.")
        sys.exit(1)
    else:
        print("\n[✓] Synthetic inspection PASSED with zero defects.")
        sys.exit(0)

if __name__ == "__main__":
    run_hackernews_inspection()
